"""Tests for batou_type pytest plugin via pytester."""

from __future__ import annotations


def _make_component(pytester, name: str, content: str) -> None:
    """Create a component file in components/ directory."""
    components = pytester.path / "components"
    components.mkdir(exist_ok=True)
    (components / name).write_text(content)


def test_batou_ty_option_accepted(pytester):
    """--batou-ty flag is accepted on an empty project without crash."""
    result = pytester.runpytest("--batou-ty", "-v")
    assert result.ret == 5  # no tests collected, but no errors


def test_markers_shows_batou_ty(pytester):
    """--markers output includes the batou_ty marker."""
    result = pytester.runpytest("--markers")
    result.stdout.fnmatch_lines(["*batou_ty*"])


def test_without_flag_component_not_collected(pytester):
    """Without --batou-ty, component .py files are not collected as special items."""
    _make_component(pytester, "comp.py", "def configure(): pass\n")
    result = pytester.runpytest("--co", "-q")
    assert result.ret == 5  # no tests collected
    assert "batou_ty" not in result.stdout.str()


def test_clean_component_passes(pytester):
    """With --batou-ty, a type-clean component is collected and passes."""
    _make_component(
        pytester,
        "comp.py",
        "def configure() -> None:\n    pass\n",
    )
    result = pytester.runpytest("--batou-ty", "-v")
    result.assert_outcomes(passed=1)


def test_error_component_fails(pytester):
    """With --batou-ty, a component with a type error fails."""
    _make_component(
        pytester,
        "bad.py",
        'def configure() -> int:\n    return "not an int"\n',
    )
    result = pytester.runpytest("--batou-ty", "-v")
    result.assert_outcomes(failed=1)


def test_non_py_files_ignored(pytester):
    """Non-.py files in components/ are ignored by the plugin."""
    components = pytester.path / "components"
    components.mkdir()
    (components / "readme.txt").write_text("not python\n")
    (components / "data.json").write_text("{}\n")
    result = pytester.runpytest("--batou-ty", "--co", "-q")
    assert result.ret == 5  # no tests collected


def test_files_outside_components_ignored(pytester):
    """Files outside components/ are ignored even with --batou-ty."""
    (pytester.path / "other.py").write_text("x: int = 1\n")
    (pytester.path / "nested").mkdir()
    (pytester.path / "nested" / "deep.py").write_text("y: int = 2\n")
    result = pytester.runpytest("--batou-ty", "--co", "-q")
    assert result.ret == 5  # no tests collected
