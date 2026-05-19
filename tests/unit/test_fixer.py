"""Unit tests for fixer transformations.

Spec decision: test-strategy — fixer functions receive source string + diagnostics,
assert on transformed source string comparison. No subprocess, no ty invocation.
"""

from batou_type.fixer import ADD_MISSING_IMPORT, Fixer, SELF_DEREF
from batou_type.output import Diagnostic


def _diag(
    message: str,
    code: str,
    file: str = "components/test.py",
    line: int = 1,
) -> Diagnostic:
    """Create a real Diagnostic for testing."""
    return Diagnostic(
        file=file,
        line=line,
        message=message,
        code=code,
        checker="ty",
    )


# -- ADD_MISSING_IMPORT -------------------------------------------------------


def test_add_missing_import_inserts_new_import() -> None:
    """Source with batou_ext.ssl access without import → from-import added."""
    source = "x = batou_ext.ssl.Certificate\n"
    diag = _diag(
        message='attribute "Certificate" of module "batou_ext.ssl"',
        code="possibly-missing-submodule",
        line=1,
    )
    result = ADD_MISSING_IMPORT.apply(source, [diag])
    assert result is not None
    assert "from batou_ext.ssl import Certificate" in result


def test_add_missing_import_merges_into_existing() -> None:
    """Existing partial import → new name merged into existing from-import."""
    source = "from batou_ext.ssl import Server\nx = batou_ext.ssl.Certificate\n"
    diag = _diag(
        message='attribute "Certificate" of module "batou_ext.ssl"',
        code="possibly-missing-submodule",
        line=2,
    )
    result = ADD_MISSING_IMPORT.apply(source, [diag])
    assert result is not None
    assert "Certificate" in result
    assert result.count("from batou_ext.ssl import") == 1


def test_add_missing_import_returns_none_when_already_present() -> None:
    """Source already has the needed import → returns None."""
    source = "from batou_ext.ssl import Certificate\nx = Certificate\n"
    diag = _diag(
        message='attribute "Certificate" of module "batou_ext.ssl"',
        code="possibly-missing-submodule",
        line=2,
    )
    result = ADD_MISSING_IMPORT.apply(source, [diag])
    assert result is None


def test_add_missing_import_returns_none_on_empty_diagnostics() -> None:
    """Empty diagnostics list → returns None."""
    result = ADD_MISSING_IMPORT.apply("x = 1\n", [])
    assert result is None


def test_add_missing_import_invalid_python_returns_none() -> None:
    """Invalid Python source → returns None gracefully."""
    source = "def foo(:\n    this is not valid\n"
    diag = _diag(
        message='attribute "X" of module "batou_ext.ssl"',
        code="possibly-missing-submodule",
    )
    result = ADD_MISSING_IMPORT.apply(source, [diag])
    assert result is None


# -- SELF_DEREF ---------------------------------------------------------------


def test_self_deref_walrus_when_deref_follows_augassign() -> None:
    """self += X followed by self._ usage → walrus operator added, self._ replaced."""
    source = "def foo(self):\n    self += X\n    y = self._.bar\n"
    diag = _diag(
        message="Object of type `Component | None` has no attribute `bar`",
        code="unresolved-attribute",
        line=3,
    )
    result = SELF_DEREF.apply(source, [diag])
    assert result is not None
    assert "_ := X" in result
    assert "self._" not in result


def test_self_deref_no_transform_without_deref() -> None:
    """self += X NOT followed by self._ → no transformation."""
    source = "def foo(self):\n    self += X\n    y = 42\n"
    diag = _diag(
        message="some unrelated error",
        code="unresolved-attribute",
        line=3,
    )
    result = SELF_DEREF.apply(source, [diag])
    assert result is None


def test_self_deref_selective_walrus_for_multiple_augassigns() -> None:
    """Multiple self += where only some have self._ → only those get walrus."""
    source = "def foo(self):\n    self += A\n    self += B\n    y = self._.bar\n"
    diag = _diag(
        message="Object of type `Component | None` has no attribute `bar`",
        code="unresolved-attribute",
        line=4,
    )
    result = SELF_DEREF.apply(source, [diag])
    assert result is not None
    assert "_ := B" in result
    assert "self += A" in result
    assert "self._" not in result


def test_self_deref_in_augassign_rhs_gets_previous_walrus() -> None:
    """self._ on the RHS of self += → previous self += gets walrus, self._ replaced."""
    source = "def foo(self):\n    self += A\n    self += Extract(self._.target)\n"
    diag = _diag(
        message="Object of type `Component | None` has no attribute `target`",
        code="unresolved-attribute",
        line=3,
    )
    result = SELF_DEREF.apply(source, [diag])
    assert result is not None
    # First self += gets walrus because self._ on RHS reads its value
    assert "_ := A" in result
    # self._ inside the Extract call is replaced with _
    assert "self._" not in result
    assert "_.target" in result
    # Second self += does NOT need walrus (no self._ after it)
    assert "Extract(_.target)" in result


def test_self_deref_in_augassign_rhs_with_subsequent_deref() -> None:
    """self._ in RHS AND after the aug → both augs get walrus."""
    source = (
        "def foo(self):\n"
        "    self += A\n"
        "    self += Extract(self._.target)\n"
        "    x = self._.bar\n"
    )
    diag = _diag(
        message="Object of type `Component | None` has no attribute `target`",
        code="unresolved-attribute",
        line=3,
    )
    result = SELF_DEREF.apply(source, [diag])
    assert result is not None
    # Both augs need walrus: first for RHS deref, second for subsequent deref
    assert "_ := A" in result
    assert "self._" not in result


def test_self_deref_returns_none_on_empty_diagnostics() -> None:
    """Empty diagnostics → returns None."""
    source = "def foo(self):\n    self += X\n    y = self._.bar\n"
    result = SELF_DEREF.apply(source, [])
    assert result is None


def test_self_deref_no_self_underscore_in_source_returns_none() -> None:
    """Source without self._ → returns None early."""
    source = "def foo(self):\n    self += X\n"
    diag = _diag(
        message="unresolved attribute",
        code="unresolved-attribute",
    )
    result = SELF_DEREF.apply(source, [diag])
    assert result is None


# -- Edge cases for both fixers -----------------------------------------------


def test_add_missing_import_empty_source() -> None:
    """Empty source with diagnostic → fixer does not crash."""
    diag = _diag(
        message='attribute "Certificate" of module "batou_ext.ssl"',
        code="possibly-missing-submodule",
    )
    result = ADD_MISSING_IMPORT.apply("", [diag])
    # Empty source parsed as empty module; import may be inserted
    assert result is None or "import" in result


def test_self_deref_empty_source_returns_none() -> None:
    """Empty source → returns None."""
    diag = _diag(
        message="unresolved attribute",
        code="unresolved-attribute",
    )
    result = SELF_DEREF.apply("", [diag])
    assert result is None


def test_self_deref_invalid_python_returns_none() -> None:
    """Invalid Python source → returns None gracefully."""
    source = "def foo(:\n    self += X\n    y = self._.bar\n"
    diag = _diag(
        message="unresolved attribute",
        code="unresolved-attribute",
    )
    result = SELF_DEREF.apply(source, [diag])
    assert result is None


# --- Fixer protocol contract ---


def test_fixer_dataclass_exists() -> None:
    """Fixer is a dataclass with __dataclass_fields__."""
    assert hasattr(Fixer, "__dataclass_fields__")


def test_fixer_has_slug_field() -> None:
    """Fixer dataclass has a 'slug' field."""
    assert "slug" in Fixer.__dataclass_fields__


def test_fixer_has_diagnostic_codes_field() -> None:
    """Fixer dataclass has a 'diagnostic_codes' field."""
    assert "diagnostic_codes" in Fixer.__dataclass_fields__


def test_add_missing_import_fixer_registered() -> None:
    """ADD_MISSING_IMPORT has correct slug and claims possibly-missing-submodule."""
    assert ADD_MISSING_IMPORT.slug == "add-missing-import"
    assert "possibly-missing-submodule" in ADD_MISSING_IMPORT.diagnostic_codes


def test_self_deref_fixer_registered() -> None:
    """SELF_DEREF has correct slug."""
    assert SELF_DEREF.slug == "self-deref"


def test_diagnostic_codes_is_frozenset() -> None:
    """Fixer diagnostic_codes field holds a frozenset."""
    assert isinstance(ADD_MISSING_IMPORT.diagnostic_codes, frozenset)


def test_fixer_apply_callable() -> None:
    """Fixer.apply is callable on registered instances."""
    assert callable(ADD_MISSING_IMPORT.apply)


# --- Import ordering contract ---


def test_add_missing_import_inserts_after_existing_imports() -> None:
    """New import goes after existing imports, before first non-import code."""
    source = "import os\n\ncomponent = batou_ext.ssl.Certificate()\n"
    diag = _diag(
        message='attribute "Certificate" of module "batou_ext.ssl"',
        code="possibly-missing-submodule",
        line=3,
    )
    result = ADD_MISSING_IMPORT.apply(source, [diag])
    assert result is not None
    lines = result.split("\n")
    from_idx = next(i for i, ln in enumerate(lines) if "from batou_ext.ssl" in ln)
    comp_idx = next(i for i, ln in enumerate(lines) if "component" in ln)
    assert from_idx < comp_idx
