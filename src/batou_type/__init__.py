"""Batou type — type-check batou deployments."""

import structlog
from importlib.metadata import PackageNotFoundError, version

from batou_type.core import (
    Checker,
    TypeCheckResult,
    check_all,
    check_file,
    find_components,
)

log = structlog.get_logger()

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
    log.debug("version-fallback", package="batou-type")
    __version__ = "0.0.0"
