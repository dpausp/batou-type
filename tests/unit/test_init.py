"""Tests for batou_type.__init__ public API."""

import re

import batou_type


def test_all_exports_importable() -> None:
    """Every name in __all__ is importable and not None."""
    for name in batou_type.__all__:
        value = getattr(batou_type, name)
        assert value is not None, f"{name} is None"


def test_version_is_string() -> None:
    """__version__ is a non-empty string matching a version pattern."""
    assert isinstance(batou_type.__version__, str)
    assert re.match(r"\d+\.\d+\.\d+", batou_type.__version__)


def test_public_api_complete() -> None:
    """__all__ contains exactly the expected public names."""
    expected = {
        "Checker",
        "CheckerError",
        "TypeCheckResult",
        "check_all",
        "check_file",
        "ensure_checker_available",
        "find_components",
        "__version__",
    }
    assert set(batou_type.__all__) == expected
