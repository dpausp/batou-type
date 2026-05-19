"""E2E tests for batou-type check --fix --diff."""
from pathlib import Path


# Component that triggers unresolved-attribute via self._ usage.
_SELF_DEREF_COMPONENT = """\
from batou.component import Component


class SubComp(Component):
    address: str = "localhost"


class MyComp(Component):
    address: str

    def configure(self):
        self += SubComp()
        addr = self._.address
"""


def test_fix_diff_exits_one_when_diffs_present(tmp_path: Path, run_cli, strip_stogger_lines) -> None:
    """--fix --diff on a project with fixable errors exits 1 (diffs present)."""
    components = tmp_path / "components"
    components.mkdir()
    (components / "comp.py").write_text(_SELF_DEREF_COMPONENT)

    result = run_cli("check", "--fix", "--diff", cwd=tmp_path)
    assert result.returncode == 1
    clean = strip_stogger_lines(result.stdout)
    assert "--- a/" in clean
    assert "+++ b/" in clean
    assert "_ := SubComp()" in clean


def test_fix_diff_exits_zero_when_clean(tmp_path: Path, run_cli) -> None:
    """--fix --diff on a clean project exits 0 (no diffs)."""
    components = tmp_path / "components"
    components.mkdir()
    (components / "comp.py").write_text("def configure():\n    pass\n")

    result = run_cli("check", "--fix", "--diff", cwd=tmp_path)
    assert result.returncode == 0


def test_fix_only_diff_output_format(tmp_path: Path, run_cli, strip_stogger_lines) -> None:
    """--fix-only --diff produces unified diff with summary line."""
    components = tmp_path / "components"
    components.mkdir()
    (components / "comp.py").write_text(_SELF_DEREF_COMPONENT)

    result = run_cli("check", "--fix-only", "--diff", cwd=tmp_path)
    assert result.returncode == 1
    clean = strip_stogger_lines(result.stdout)
    assert "--- a/" in clean
    assert "+++ b/" in clean
    assert "fixable" in (result.stdout + result.stderr).lower()
    # File should NOT be modified (--diff is read-only)
    source = (components / "comp.py").read_text()
    assert "self._.address" in source
