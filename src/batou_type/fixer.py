"""libcst-based autofix for common batou type-check diagnostics.

Spec decision: module-placement — new module between cli.py and output.py.
Imports: Diagnostic from batou_type.output, libcst. Nothing else from batou_type.
"""

import re
from dataclasses import dataclass

import libcst as cst

from batou_type.output import Diagnostic

# ---------------------------------------------------------------------------
# Fixer protocol — fixer-protocol
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Fixer:
    """A single autofix: claims diagnostics by code, transforms source.

    Spec decision: fixer-protocol — dataclass with slug, diagnostic_codes, apply.
    """

    slug: str
    diagnostic_codes: frozenset[str]

    def apply(self, source: str, diagnostics: list[Diagnostic]) -> str | None:
        match self.slug:
            case "add-missing-import":
                return _apply_add_missing_import(source, diagnostics)
            case "self-deref":
                return _apply_self_deref(source, diagnostics)
            case _:
                return None


# ---------------------------------------------------------------------------
# Fixer instances — diagnostic-matching
# ---------------------------------------------------------------------------

ADD_MISSING_IMPORT = Fixer(
    slug="add-missing-import",
    diagnostic_codes=frozenset({"possibly-missing-submodule"}),
)

SELF_DEREF = Fixer(
    slug="self-deref",
    diagnostic_codes=frozenset({"unresolved-attribute"}),
)


# ---------------------------------------------------------------------------
# add-missing-import — add-missing-import-impl
# ---------------------------------------------------------------------------


def _apply_add_missing_import(source: str, diagnostics: list[Diagnostic]) -> str | None:
    """Insert missing from-imports for possibly-missing-submodule diagnostics.

    Spec decision: add-missing-import-impl — extract module path from
    diagnostic message, use libcst to parse AST, check existing imports,
    merge or insert new from-import.
    """
    if not diagnostics:
        return None

    imports_to_add: dict[str, set[str]] = {}
    for diag in diagnostics:
        if diag.code != "possibly-missing-submodule":
            continue
        module_path, name = _extract_module_and_name(diag, source)
        if module_path and name:
            imports_to_add.setdefault(module_path, set()).add(name)

    if not imports_to_add:
        return None

    try:
        tree = cst.parse_module(source)
    except cst.ParserSyntaxError:
        return None

    existing = _collect_existing_imports(tree)

    actually_new: dict[str, set[str]] = {}
    for mod, names in imports_to_add.items():
        if mod in existing:
            missing = names - existing[mod]
            if missing:
                actually_new[mod] = missing
        else:
            actually_new[mod] = names

    if not actually_new:
        return None

    transformer = _ImportInserter(actually_new)
    new_tree = tree.visit(transformer)
    result = new_tree.code
    return result if result != source else None


def _extract_module_and_name(
    diag: Diagnostic, source: str
) -> tuple[str | None, str | None]:
    """Extract module path and importable name from a diagnostic.

    Spec decision: add-missing-import-impl — 'Class/function name extracted
    from the offending line via libcst AST analysis.'
    """
    message = diag.message

    # Pattern: attribute "X" of module "Y.Z"
    match = re.search(
        r'attribute\s+["\'](\w+)["\'].*module\s+["\']([\w.]+)["\']', message
    )
    if match:
        attr, parent = match.group(1), match.group(2)
        return parent, attr

    # Pattern: dotted name in quotes e.g. "batou_ext.ssl"
    match = re.search(r'["\']([\w]+\.[\w.]+)["\']', message)
    if match:
        full = match.group(1)
        parts = full.rsplit(".", 1)
        if len(parts) == 2:
            return full, parts[1]

    # Fallback: inspect the offending source line
    lines = source.splitlines()
    if 0 < diag.line <= len(lines):
        line = lines[diag.line - 1]
        match = re.search(r"([\w]+\.[\w]+)\.(\w+)", line)
        if match:
            return match.group(1), match.group(2)

    return None, None


def _collect_existing_imports(tree: cst.Module) -> dict[str, set[str]]:
    """Walk top-level statements for from-import declarations."""
    existing: dict[str, set[str]] = {}
    for stmt in tree.body:
        if not isinstance(stmt, cst.SimpleStatementLine):
            continue
        for item in stmt.body:
            if not isinstance(item, cst.ImportFrom) or not item.module:
                continue
            module = _dotted_name(item.module)
            if not module or not isinstance(item.names, list | tuple):
                continue
            names: set[str] = set()
            for alias in item.names:
                if isinstance(alias, cst.ImportAlias) and alias.name:
                    names.add(_node_text(alias.name))
            existing.setdefault(module, set()).update(names)
    return existing


class _ImportInserter(cst.CSTTransformer):
    """Insert or merge from-import statements.

    Spec decision: add-missing-import-impl — 'merge new name into existing
    from X import ... statement. If not → insert new from-import at file top.'
    """

    def __init__(self, new_imports: dict[str, set[str]]) -> None:
        self._remaining = dict(new_imports)

    def leave_ImportFrom(
        self,
        original_node: cst.ImportFrom,
        updated_node: cst.ImportFrom,
    ) -> cst.ImportFrom:
        if not updated_node.module:
            return updated_node
        module = _dotted_name(updated_node.module)
        if module not in self._remaining or not isinstance(
            updated_node.names, list | tuple
        ):
            return updated_node

        new_names = self._remaining.pop(module)
        aliases = list(updated_node.names)
        for name in sorted(new_names):
            aliases.append(cst.ImportAlias(name=cst.Name(name)))
        return updated_node.with_changes(names=aliases)

    def leave_Module(
        self,
        original_node: cst.Module,
        updated_node: cst.Module,
    ) -> cst.Module:
        if not self._remaining:
            return updated_node

        new_stmts: list[cst.SimpleStatementLine] = []
        for mod_path, names in sorted(self._remaining.items()):
            aliases = [cst.ImportAlias(name=cst.Name(n)) for n in sorted(names)]
            import_node = cst.ImportFrom(
                module=_build_dotted_name(mod_path),
                names=aliases,
            )
            new_stmts.append(cst.SimpleStatementLine(body=[import_node]))

        insert_idx = 0
        for i, stmt in enumerate(updated_node.body):
            if isinstance(stmt, cst.SimpleStatementLine):
                for item in stmt.body:
                    if isinstance(item, (cst.Import, cst.ImportFrom)):
                        insert_idx = i + 1

        new_body = list(updated_node.body)
        for j, stmt in enumerate(new_stmts):
            new_body.insert(insert_idx + j, stmt)

        return updated_node.with_changes(body=new_body)


# ---------------------------------------------------------------------------
# self-deref — self-deref-impl
# ---------------------------------------------------------------------------


def _apply_self_deref(source: str, diagnostics: list[Diagnostic]) -> str | None:
    """Transform self._ references using walrus operator on self += assignments.

    Spec decision: self-deref-impl — 'Two-pass libcst transformation: scan for
    self._ references, transform self += X to self += (_ := X) only where
    _ is referenced, replace self._ with _.'
    """
    if not diagnostics:
        return None

    relevant = [d for d in diagnostics if d.code in SELF_DEREF.diagnostic_codes]
    if not relevant:
        return None

    # Quick pre-check before parsing
    if "self._" not in source:
        return None

    try:
        tree = cst.parse_module(source)
    except cst.ParserSyntaxError:
        return None

    # Pass 1: scope-aware analysis
    analyzer = _SelfDerefAnalyzer()
    tree.visit(analyzer)

    if not analyzer.has_self_deref:
        return None

    # Pass 2: transform only where analysis determined it's needed
    transformer = _SelfDerefTransformer(
        needs_walrus=analyzer.needs_walrus,
        derefs_to_replace=analyzer.derefs_to_replace,
    )
    new_tree = tree.visit(transformer)
    result = new_tree.code
    return result if result != source else None


class _SelfDerefAnalyzer(cst.CSTVisitor):
    """Scope-aware analysis: determine which self += need walrus.

    Spec decision: self-deref-impl — 'check if any self._ reference exists
    between it and the next self += (or end of function).'
    """

    def __init__(self) -> None:
        self.needs_walrus: set[int] = set()
        self.derefs_to_replace: set[int] = set()
        self.has_self_deref = False
        self._scope_stack: list[list[tuple[str, int]]] = []
        self._current_self_aug: int | None = None

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        self._scope_stack.append([])
        return True

    def leave_FunctionDef(self, original_node: cst.FunctionDef) -> None:
        events = self._scope_stack.pop()
        self._analyze_events(events)

    def visit_AugAssign(self, node: cst.AugAssign) -> bool:
        if (
            isinstance(node.target, cst.Name)
            and node.target.value == "self"
            and isinstance(node.operator, cst.AddAssign)
        ):
            self._current_self_aug = id(node)
        return True

    def leave_AugAssign(self, original_node: cst.AugAssign) -> None:
        if (
            isinstance(original_node.target, cst.Name)
            and original_node.target.value == "self"
            and isinstance(original_node.operator, cst.AddAssign)
        ):
            # Append aug event AFTER children so that self._ derefs on the RHS
            # appear before this aug in the event list, correlating them with
            # the *previous* self += instead.
            if self._scope_stack:
                self._scope_stack[-1].append(("aug", id(original_node)))
            self._current_self_aug = None

    def visit_Attribute(self, node: cst.Attribute) -> bool:
        if (
            isinstance(node.value, cst.Name)
            and node.value.value == "self"
            and node.attr.value == "_"
            and self._scope_stack
        ):
            self._scope_stack[-1].append(("deref", id(node)))
            self.has_self_deref = True
        return True

    def _analyze_events(self, events: list[tuple[str, int]]) -> None:
        """Determine which self += statements need walrus wrapping."""
        aug_positions = [
            (i, nid) for i, (kind, nid) in enumerate(events) if kind == "aug"
        ]

        for idx, (pos, aug_id) in enumerate(aug_positions):
            end = (
                aug_positions[idx + 1][0]
                if idx + 1 < len(aug_positions)
                else len(events)
            )
            deref_ids = [
                nid
                for j, (kind, nid) in enumerate(events)
                if kind == "deref" and pos < j < end
            ]
            if deref_ids:
                self.needs_walrus.add(aug_id)
                self.derefs_to_replace.update(deref_ids)


class _SelfDerefTransformer(cst.CSTTransformer):
    """Replace self._ with _ and wrap self += X with walrus — scope-aware.

    Spec decision: self-deref-impl — 'transform self += X to self += (_ := X)
    only where self._ is referenced, replace self._ references with _.
    Scope is sequential statement order within the same function.'
    """

    def __init__(
        self,
        needs_walrus: set[int],
        derefs_to_replace: set[int],
    ) -> None:
        self._needs_walrus = needs_walrus
        self._derefs_to_replace = derefs_to_replace

    def leave_Attribute(
        self,
        original_node: cst.Attribute,
        updated_node: cst.Attribute,
    ) -> cst.Attribute | cst.Name:
        if id(original_node) in self._derefs_to_replace:
            return cst.Name("_")
        return updated_node

    def leave_AugAssign(
        self,
        original_node: cst.AugAssign,
        updated_node: cst.AugAssign,
    ) -> cst.AugAssign:
        if id(original_node) not in self._needs_walrus:
            return updated_node
        if isinstance(updated_node.value, cst.NamedExpr):
            return updated_node
        walrus = cst.NamedExpr(
            target=cst.Name("_"),
            value=updated_node.value,
            lpar=[cst.LeftParen()],
            rpar=[cst.RightParen()],
        )
        return updated_node.with_changes(value=walrus)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dotted_name(node: cst.BaseExpression) -> str:
    """Reconstruct a dotted name from libcst Attribute/Name nodes."""
    parts: list[str] = []

    def _collect(n: cst.BaseExpression) -> None:
        if isinstance(n, cst.Attribute):
            _collect(n.value)
            parts.append(n.attr.value)
        elif isinstance(n, cst.Name):
            parts.append(n.value)

    _collect(node)
    return ".".join(parts)


def _node_text(node: cst.BaseAssignTargetExpression) -> str:
    """Get text representation of a name node."""
    if isinstance(node, cst.Name):
        return node.value
    return _dotted_name(node)


def _build_dotted_name(name: str) -> cst.Attribute | cst.Name:
    """Build a libcst dotted-name expression from a string like 'a.b.c'."""
    parts = name.split(".")
    result: cst.Attribute | cst.Name = cst.Name(parts[0])
    for part in parts[1:]:
        result = cst.Attribute(value=result, attr=cst.Name(part))
    return result
