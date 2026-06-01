"""Project setup: copy stubs, write checker config to pyproject.toml.

Stdlib + structlog + tomli-w only. No imports from other batou_type modules.
"""

import re
import shutil
import tomllib
from pathlib import Path
from typing import Any

import structlog
import tomli_w

log = structlog.get_logger()

MANAGED_MARKER: str = "# managed by batou-type setup"

VALID_CHECKERS: list[str] = ["ty", "mypy", "pyright"]

CHECKER_CONFIGS: dict[str, dict] = {
    "ty": {
        "environment": {"extra-paths": ["stubs"]},
        "src": {"include": ["components"]},
    },
    "mypy": {
        "mypy_path": "stubs",
        "explicit_package_bases": True,
        "check_untyped_defs": True,
        "files": ["components"],
        "python_executable": ".venv/bin/python",
    },
    "pyright": {
        "include": ["components"],
        "stubPath": "stubs",
        "venvPath": ".",
        "venv": ".venv",
    },
}


class SetupError(Exception):
    """Error during project setup for type checking."""

    def __init__(
        self, message: str, conflicting_sections: list[str] | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.conflicting_sections: list[str] = conflicting_sections or []
        log.debug(
            "setup-error", message=message, conflicting=conflicting_sections or []
        )


def copy_stubs(target_dir: Path, vendor_dir: Path) -> list[Path]:
    """Copy vendored stubs to target project's stubs/ directory.

    Copies vendor_dir/batou/, batou_ext/, execnet/, and configupdater/ into
    target_dir/stubs/. Idempotent: overwrites existing files.
    """
    copied: list[Path] = []
    for pkg in ("batou", "batou_ext", "execnet", "configupdater"):
        src = vendor_dir / pkg
        dst = target_dir / "stubs" / pkg
        shutil.copytree(src, dst, dirs_exist_ok=True)
        for p in dst.rglob("*"):
            if p.is_file():
                copied.append(p)
    log.info(
        "stubs-copied",
        count=len(copied),
        _replace_msg="Copied {count} stub file(s) to stubs/",
    )
    return copied


def _is_checker_section(line: str, checker: str) -> bool:
    """Return True if line is a TOML section header for the given checker.

    Matches both exact ``[tool.{checker}]`` and nested tables like
    ``[tool.{checker}.environment]``.
    """
    stripped = line.strip()
    prefix = f"[tool.{checker}"
    if not stripped.startswith(prefix):
        return False
    next_char = stripped[len(prefix) : len(prefix) + 1]
    matched = next_char in ("]", ".")
    if matched:
        log.debug("checker-section-found", header=stripped)
    return matched


def _find_unmanaged_sections(raw_text: str, checkers: list[str]) -> list[str]:
    """Find checker sections that exist without the managed marker."""
    conflicting: list[str] = []
    lines = raw_text.splitlines()

    for checker in checkers:
        for i, line in enumerate(lines):
            if _is_checker_section(line, checker):
                marker_found = False
                for j in range(i - 1, -1, -1):
                    stripped = lines[j].strip()
                    if stripped == "":
                        continue
                    if stripped == MANAGED_MARKER:
                        marker_found = True
                    break

                if not marker_found:
                    conflicting.append(line.strip())
                break

    if conflicting:
        log.debug("unmanaged-sections", count=len(conflicting), sections=conflicting)
    return conflicting


def _inline_arrays(toml_str: str) -> str:
    """Convert tomli_w multi-line arrays to inline format."""
    pattern = r'([\w-]+) = \[\n((?:\s*"[^"]*",?\n)+)\]'

    def _replacer(match: re.Match[str]) -> str:
        key = match.group(1)
        content = match.group(2)
        values = re.findall(r'"([^"]*)"', content)
        formatted = ", ".join(f'"{v}"' for v in values)
        return f"{key} = [{formatted}]"

    return re.sub(pattern, _replacer, toml_str)


def _insert_markers(toml_str: str, checkers: list[str]) -> str:
    """Insert MANAGED_MARKER comment before managed [tool.xxx] sections."""
    lines = toml_str.splitlines()
    for checker in checkers:
        for i, line in enumerate(lines):
            if _is_checker_section(line, checker):
                header = line.strip()
                # Check if marker already on line before
                if i > 0 and lines[i - 1].strip() == MANAGED_MARKER:
                    log.debug("marker-exists", header=header)
                else:
                    lines.insert(i, MANAGED_MARKER)
                    log.debug("marker-inserted", header=header)
                break
    return "\n".join(lines)


def write_checker_config(
    target_dir: Path,
    checkers: list[str],
    dry_run: bool = False,
) -> str | None:
    """Write checker configuration to pyproject.toml.

    Reads existing pyproject.toml if present, checks for unmanaged checker
    sections, and writes checker config with managed markers.

    Args:
        target_dir: Project directory containing pyproject.toml.
        checkers: Checker names to configure (subset of VALID_CHECKERS).
        dry_run: If True, return TOML content without writing to disk.

    Returns:
        TOML content string. None if no pyproject.toml existed before.

    Raises:
        SetupError: If unmanaged checker sections are found.
    """
    pyproject = target_dir / "pyproject.toml"
    had_existing = pyproject.exists()

    if had_existing:
        raw_text = pyproject.read_text()
        data = tomllib.loads(raw_text)
        conflicting = _find_unmanaged_sections(raw_text, checkers)
        if conflicting:
            sections = ", ".join(conflicting)
            raise SetupError(
                f"Existing unmanaged checker sections: {sections}",
                conflicting_sections=conflicting,
            )
    else:
        data: dict[str, Any] = {
            "project": {"name": target_dir.name, "version": "0.1.0"}
        }

    tool = data.setdefault("tool", {})
    for checker in checkers:
        tool[checker] = CHECKER_CONFIGS[checker]

    toml_str = tomli_w.dumps(data)
    toml_str = _inline_arrays(toml_str)
    toml_str = _insert_markers(toml_str, checkers)

    if dry_run:
        return toml_str

    pyproject.write_text(toml_str)
    log.info(
        "checker-config-written",
        _replace_msg="Wrote config for {checkers}",
        checkers=", ".join(checkers),
    )

    if had_existing:
        return toml_str
    return None
