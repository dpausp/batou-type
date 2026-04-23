"""Batou type — type-check batou deployments."""

from importlib.metadata import PackageNotFoundError, version

from batou_type.core import (
    Checker,
    TypeCheckResult,
    check_all,
    check_file,
    find_components,
)

__all__ = [
    "Checker",
    "TypeCheckResult",
    "check_all",
    "check_file",
    "find_components",
    "__version__",
]

try:
    __version__ = version("batou-type")
except PackageNotFoundError:
    __version__ = "0.0.0"
