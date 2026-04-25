"""Unit tests for batou_type.core pure path functions."""

import os
import stat
from pathlib import Path

from batou_type.core import find_components, find_project_venv, is_batou_project


class TestFindProjectVenv:
    """Tests for find_project_venv(project: Path) -> VenvInfo | None."""

    def test_no_venv_returns_none(self, tmp_path: Path) -> None:
        assert find_project_venv(tmp_path) is None

    def test_dot_venv_with_pyvenv_cfg(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").touch()
        result = find_project_venv(tmp_path)
        assert result is not None
        assert result.label == ".venv"
        assert result.path == str(venv)
        assert not result.is_appenv

    def test_dot_venv_with_lib_dir(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "lib").mkdir()
        result = find_project_venv(tmp_path)
        assert result is not None
        assert result.label == ".venv"

    def test_dot_venv_empty_returns_none(self, tmp_path: Path) -> None:
        (tmp_path / ".venv").mkdir()
        assert find_project_venv(tmp_path) is None

    def test_appenv_script(self, tmp_path: Path) -> None:
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

    def test_appenv_failing_script_returns_none(self, tmp_path: Path) -> None:
        appenv = tmp_path / "appenv"
        appenv.write_text("#!/bin/sh\nexit 1\n")
        appenv.chmod(appenv.stat().st_mode | stat.S_IEXEC)
        assert find_project_venv(tmp_path) is None

    def test_appenv_directory_returns_none(self, tmp_path: Path) -> None:
        (tmp_path / "appenv").mkdir()
        assert find_project_venv(tmp_path) is None

    def test_dot_venv_takes_priority_over_appenv(self, tmp_path: Path) -> None:
        dot_venv = tmp_path / ".venv"
        dot_venv.mkdir()
        (dot_venv / "pyvenv.cfg").touch()

        appenv = tmp_path / "appenv"
        appenv.write_text("#!/bin/sh\nshift\necho '/fake'\n")
        appenv.chmod(appenv.stat().st_mode | stat.S_IEXEC)

        result = find_project_venv(tmp_path)
        assert result is not None
        assert result.label == ".venv"

    def test_dot_venv_is_file_returns_none(self, tmp_path: Path) -> None:
        (tmp_path / ".venv").touch()  # file, not directory
        assert find_project_venv(tmp_path) is None

    def test_dot_venv_site_packages(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        sp = venv / "lib" / "python3.14" / "site-packages"
        sp.mkdir(parents=True)
        result = find_project_venv(tmp_path)
        assert result is not None
        assert str(sp) in result.site_packages

    def test_dot_venv_multiple_python_versions(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        sp1 = venv / "lib" / "python3.12" / "site-packages"
        sp1.mkdir(parents=True)
        sp2 = venv / "lib" / "python3.14" / "site-packages"
        sp2.mkdir(parents=True)
        result = find_project_venv(tmp_path)
        assert result is not None
        assert len(result.site_packages) == 2


class TestIsBatouProject:
    """Tests for is_batou_project(directory: Path) -> bool."""

    def test_with_components_dir(self, tmp_path: Path) -> None:
        (tmp_path / "components").mkdir()
        assert is_batou_project(tmp_path) is True

    def test_without_components_dir(self, tmp_path: Path) -> None:
        assert is_batou_project(tmp_path) is False

    def test_components_is_file_not_dir(self, tmp_path: Path) -> None:
        (tmp_path / "components").touch()
        assert is_batou_project(tmp_path) is False

    def test_nested_components_dir(self, tmp_path: Path) -> None:
        project = tmp_path / "myproject"
        project.mkdir()
        (project / "components").mkdir()
        assert is_batou_project(project) is True


class TestFindComponents:
    """Tests for find_components(root: Path) -> list[Path]."""

    def test_no_components_dir_returns_empty(self, tmp_path: Path) -> None:
        assert find_components(tmp_path) == []

    def test_empty_components_dir_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "components").mkdir()
        assert find_components(tmp_path) == []

    def test_finds_python_files(self, tmp_path: Path) -> None:
        comp = tmp_path / "components"
        comp.mkdir()
        f1 = comp / "mycomp.py"
        f1.touch()
        f2 = comp / "other.py"
        f2.touch()
        assert find_components(tmp_path) == sorted([f1, f2])

    def test_ignores_non_py_files(self, tmp_path: Path) -> None:
        comp = tmp_path / "components"
        comp.mkdir()
        py_file = comp / "component.py"
        py_file.touch()
        (comp / "data.json").touch()
        (comp / "config.yaml").touch()
        assert find_components(tmp_path) == [py_file]

    def test_nested_py_files(self, tmp_path: Path) -> None:
        comp = tmp_path / "components"
        sub = comp / "sub" / "deep"
        sub.mkdir(parents=True)
        f1 = comp / "top.py"
        f1.touch()
        f2 = sub / "nested.py"
        f2.touch()
        assert find_components(tmp_path) == sorted([f1, f2])

    def test_results_are_sorted(self, tmp_path: Path) -> None:
        comp = tmp_path / "components"
        comp.mkdir()
        files = []
        for name in ["c_comp.py", "a_comp.py", "b_comp.py"]:
            f = comp / name
            f.touch()
            files.append(f)
        result = find_components(tmp_path)
        assert result == sorted(files)
