"""Root conftest — session-wide test configuration."""
import re

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

pytest_plugins = ["pytester"]

def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return _ANSI_RE.sub("", text)
