"""Unit tests for fixer transformations.

Spec decision: test-strategy — fixer functions receive source string + diagnostics,
assert on transformed source string comparison. No subprocess, no ty invocation.
"""

from batou_type.fixer import ADD_MISSING_IMPORT, SELF_DEREF
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
