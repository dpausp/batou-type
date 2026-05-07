"""Batou type — type-check batou deployments."""

from importlib.metadata import PackageNotFoundError, version

import structlog

from batou_type.core import (
    Checker,
    CheckerError,
    TypeCheckResult,
    check_all,
    check_file,
    ensure_checker_available,
    find_components,
)

log = structlog.get_logger()

__all__ = [
    "Checker",
    "CheckerError",
    "TypeCheckResult",
    "check_all",
    "check_file",
    "ensure_checker_available",
    "find_components",
    "__version__",
]

try:
    __version__ = version("batou-type")
except PackageNotFoundError:
    log.debug("version-fallback", package="batou-type")
    __version__ = "0.0.0"
