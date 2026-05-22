"""Unit tests for batou_type.core domain functions."""

import stat
import sys
from pathlib import Path

import pytest

from batou_type.core import (
    Checker,
    CheckerError,
    TypeCheckResult,
    check_all,
    check_file,
    ensure_checker_available,
    find_components,
    find_project_venv,
    is_batou_project,
)


# --- find_project_venv ---


def test_no_venv_returns_none(tmp_path: Path) -> None:
    assert find_project_venv(tmp_path) is None


def test_dot_venv_with_pyvenv_cfg(tmp_path: Path) -> None:
    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / "pyvenv.cfg").touch()
    result = find_project_venv(tmp_path)
    assert result is not None
    assert result.label == ".venv"
    assert result.path == str(venv)
    assert not result.is_appenv


def test_dot_venv_with_lib_dir(tmp_path: Path) -> None:
    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / "lib").mkdir()
    result = find_project_venv(tmp_path)
    assert result is not None
    assert result.label == ".venv"


def test_dot_venv_empty_returns_none(tmp_path: Path) -> None:
    (tmp_path / ".venv").mkdir()
    assert find_project_venv(tmp_path) is None


def test_appenv_script(tmp_path: Path) -> None:
    site_pkg = tmp_path / "appenv_lib" / "python3.14" / "site-packages"
    site_pkg.mkdir(parents=True)
    appenv = tmp_path / "appenv"
    appenv.write_text(f"#!/bin/sh\nshift\necho '{site_pkg}'\n")
    appenv.chmod(appenv.stat().st_mode | stat.S_IEXEC)
    result = find_project_venv(tmp_path)
    assert result is not None
    assert result.label == "appenv"
    assert result.is_appenv
    assert result.site_packages == [str(site_pkg)]


def test_appenv_failing_script_returns_none(tmp_path: Path) -> None:
    appenv = tmp_path / "appenv"
    appenv.write_text("#!/bin/sh\nexit 1\n")
    appenv.chmod(appenv.stat().st_mode | stat.S_IEXEC)
    assert find_project_venv(tmp_path) is None


def test_appenv_directory_returns_none(tmp_path: Path) -> None:
    (tmp_path / "appenv").mkdir()
    assert find_project_venv(tmp_path) is None


def test_dot_venv_takes_priority_over_appenv(tmp_path: Path) -> None:
    dot_venv = tmp_path / ".venv"
    dot_venv.mkdir()
    (dot_venv / "pyvenv.cfg").touch()

    appenv = tmp_path / "appenv"
    appenv.write_text("#!/bin/sh\nshift\necho '/fake'\n")
    appenv.chmod(appenv.stat().st_mode | stat.S_IEXEC)

    result = find_project_venv(tmp_path)
    assert result is not None
    assert result.label == ".venv"


def test_dot_venv_is_file_returns_none(tmp_path: Path) -> None:
    (tmp_path / ".venv").touch()  # file, not directory
    assert find_project_venv(tmp_path) is None


def test_dot_venv_site_packages(tmp_path: Path) -> None:
    venv = tmp_path / ".venv"
    sp = venv / "lib" / "python3.14" / "site-packages"
    sp.mkdir(parents=True)
    result = find_project_venv(tmp_path)
    assert result is not None
    assert str(sp) in result.site_packages


def test_dot_venv_multiple_python_versions(tmp_path: Path) -> None:
    venv = tmp_path / ".venv"
    sp1 = venv / "lib" / "python3.12" / "site-packages"
    sp1.mkdir(parents=True)
    sp2 = venv / "lib" / "python3.14" / "site-packages"
    sp2.mkdir(parents=True)
    result = find_project_venv(tmp_path)
    assert result is not None
    assert len(result.site_packages) == 2


# --- is_batou_project ---


def test_is_batou_project_with_components_dir(tmp_path: Path) -> None:
    (tmp_path / "components").mkdir()
    assert is_batou_project(tmp_path) is True


def test_is_batou_project_without_components_dir(tmp_path: Path) -> None:
    assert is_batou_project(tmp_path) is False


def test_is_batou_project_components_is_file_not_dir(tmp_path: Path) -> None:
    (tmp_path / "components").touch()
    assert is_batou_project(tmp_path) is False


def test_is_batou_project_nested_components_dir(tmp_path: Path) -> None:
    project = tmp_path / "myproject"
    project.mkdir()
    (project / "components").mkdir()
    assert is_batou_project(project) is True


# --- find_components ---


def test_find_components_no_components_dir_returns_empty(tmp_path: Path) -> None:
    assert find_components(tmp_path) == []


def test_find_components_empty_components_dir_returns_empty(tmp_path: Path) -> None:
    (tmp_path / "components").mkdir()
    assert find_components(tmp_path) == []


def test_find_components_finds_python_files(tmp_path: Path) -> None:
    comp = tmp_path / "components"
    comp.mkdir()
    f1 = comp / "mycomp.py"
    f1.touch()
    f2 = comp / "other.py"
    f2.touch()
    assert find_components(tmp_path) == sorted([f1, f2])


def test_find_components_ignores_non_py_files(tmp_path: Path) -> None:
    comp = tmp_path / "components"
    comp.mkdir()
    py_file = comp / "component.py"
    py_file.touch()
    (comp / "data.json").touch()
    (comp / "config.yaml").touch()
    assert find_components(tmp_path) == [py_file]


def test_find_components_nested_py_files(tmp_path: Path) -> None:
    comp = tmp_path / "components"
    sub = comp / "sub" / "deep"
    sub.mkdir(parents=True)
    f1 = comp / "top.py"
    f1.touch()
    f2 = sub / "nested.py"
    f2.touch()
    assert find_components(tmp_path) == sorted([f1, f2])


def test_find_components_results_are_sorted(tmp_path: Path) -> None:
    comp = tmp_path / "components"
    comp.mkdir()
    files = []
    for name in ["c_comp.py", "a_comp.py", "b_comp.py"]:
        f = comp / name
        f.touch()
        files.append(f)
    result = find_components(tmp_path)
    assert result == sorted(files)


# --- ensure_checker_available ---


def test_ensure_checker_available_ty_succeeds() -> None:
    """ty is installed in this project."""
    ensure_checker_available(Checker.ty)


def test_ensure_checker_available_missing_checker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CheckerError raised when checker binary exits non-zero."""
    fake_python = tmp_path / "fake_python"
    fake_python.write_text("#!/bin/sh\necho 'No module named ty' >&2\nexit 1\n")
    fake_python.chmod(fake_python.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setattr(sys, "executable", str(fake_python))
    with pytest.raises(CheckerError, match="not available"):
        ensure_checker_available(Checker.ty)


# --- check_file ---


def test_check_file_clean(tmp_path: Path) -> None:
    """Type-checking a clean file returns has_errors=False."""
    f = tmp_path / "clean.py"
    f.write_text("x: int = 42\n")
    result = check_file(str(f), [Checker.ty])
    assert isinstance(result, TypeCheckResult)
    assert not result.has_errors
    assert result.path == str(f)


def test_check_file_with_type_error(tmp_path: Path) -> None:
    """Type-checking a file with a type error returns has_errors=True."""
    f = tmp_path / "error.py"
    f.write_text('x: int = "string"\n')
    result = check_file(str(f), [Checker.ty])
    assert isinstance(result, TypeCheckResult)
    assert result.has_errors
    assert "invalid-assignment" in result.output or "string" in result.output


def test_check_file_json_mode_with_error(tmp_path: Path) -> None:
    """json_mode=True returns parsed Diagnostic errors on failure."""
    f = tmp_path / "error.py"
    f.write_text('x: int = "string"\n')
    result = check_file(str(f), [Checker.ty], json_mode=True)
    assert result.has_errors
    assert result.errors is not None
    assert len(result.errors) > 0
    assert result.errors[0].checker == "ty"
    assert result.errors[0].line == 1
    assert result.errors[0].code == "invalid-assignment"


def test_check_file_json_mode_clean(tmp_path: Path) -> None:
    """json_mode=True with a clean file returns no parsed errors."""
    f = tmp_path / "clean.py"
    f.write_text("x: int = 42\n")
    result = check_file(str(f), [Checker.ty], json_mode=True)
    assert not result.has_errors
    assert result.errors is None


def test_check_file_extra_search_paths(tmp_path: Path) -> None:
    """extra_search_paths are forwarded to ty as --extra-search-path flags."""
    f = tmp_path / "clean.py"
    f.write_text("x: int = 42\n")
    extra = tmp_path / "stubs"
    extra.mkdir()
    result = check_file(str(f), [Checker.ty], extra_search_paths=[str(extra)])
    assert not result.has_errors
    assert "--extra-search-path" in result.command
    assert str(extra) in result.command


# --- check_all ---


def test_check_all_with_components(tmp_path: Path) -> None:
    """check_all type-checks all .py files in components/."""
    comp = tmp_path / "components"
    comp.mkdir()
    (comp / "app.py").write_text("x: int = 42\n")
    (comp / "db.py").write_text("y: str = 'hello'\n")
    results = check_all(tmp_path, checkers=[Checker.ty])
    assert len(results) == 2
    paths = {r.path for r in results}
    assert "components/app.py" in paths
    assert "components/db.py" in paths
    assert all(not r.has_errors for r in results)


def test_check_all_non_project_dir(tmp_path: Path) -> None:
    """check_all with no components/ dir returns empty list."""
    results = check_all(tmp_path)
    assert results == []


def test_check_all_with_type_errors(tmp_path: Path) -> None:
    """check_all reports errors and parsed diagnostics for bad files."""
    comp = tmp_path / "components"
    comp.mkdir()
    (comp / "bad.py").write_text('x: int = "not an int"\n')
    (comp / "good.py").write_text("y: int = 42\n")
    results = check_all(tmp_path, checkers=[Checker.ty], json_mode=True)
    assert len(results) == 2
    bad = [r for r in results if "bad.py" in r.path][0]
    good = [r for r in results if "good.py" in r.path][0]
    assert bad.has_errors
    assert bad.errors is not None
    assert len(bad.errors) > 0
    assert not good.has_errors
