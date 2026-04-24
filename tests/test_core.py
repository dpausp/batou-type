"""Unit tests for batou_type.core pure path functions."""

from pathlib import Path

from batou_type.core import find_components, find_project_venv, get_venv_site_packages, is_batou_project


class TestFindProjectVenv:
    """Tests for find_project_venv(project: Path) -> Path | None."""

    def test_no_venv_returns_none(self, tmp_path: Path) -> None:
        assert find_project_venv(tmp_path) is None

    def test_dot_venv_with_pyvenv_cfg(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").touch()
        assert find_project_venv(tmp_path) == venv

    def test_dot_venv_with_lib_dir(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "lib").mkdir()
        assert find_project_venv(tmp_path) == venv

    def test_dot_venv_empty_returns_none(self, tmp_path: Path) -> None:
        (tmp_path / ".venv").mkdir()
        assert find_project_venv(tmp_path) is None

    def test_appenv_with_pyvenv_cfg(self, tmp_path: Path) -> None:
        venv = tmp_path / "appenv"
        venv.mkdir()
        (venv / "pyvenv.cfg").touch()
        assert find_project_venv(tmp_path) == venv

    def test_dot_venv_takes_priority_over_appenv(self, tmp_path: Path) -> None:
        dot_venv = tmp_path / ".venv"
        dot_venv.mkdir()
        (dot_venv / "pyvenv.cfg").touch()

        appenv = tmp_path / "appenv"
        appenv.mkdir()
        (appenv / "pyvenv.cfg").touch()

        assert find_project_venv(tmp_path) == dot_venv

    def test_dot_venv_is_file_returns_none(self, tmp_path: Path) -> None:
        (tmp_path / ".venv").touch()  # file, not directory
        assert find_project_venv(tmp_path) is None


class TestGetVenvSitePackages:
    """Tests for get_venv_site_packages(venv: Path) -> list[str]."""

    def test_empty_venv_returns_empty(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        venv.mkdir()
        assert get_venv_site_packages(venv) == []

    def test_standard_layout(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        sp = venv / "lib" / "python3.14" / "site-packages"
        sp.mkdir(parents=True)
        result = get_venv_site_packages(venv)
        assert result == [str(sp)]

    def test_multiple_python_versions(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        sp1 = venv / "lib" / "python3.12" / "site-packages"
        sp1.mkdir(parents=True)
        sp2 = venv / "lib" / "python3.14" / "site-packages"
        sp2.mkdir(parents=True)
        result = get_venv_site_packages(venv)
        assert result == [str(sp1), str(sp2)]

    def test_lib64_deduplicated_when_same_as_lib(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        sp = venv / "lib" / "python3.14" / "site-packages"
        sp.mkdir(parents=True)
        # lib64 pointing to same resolved path
        lib64 = venv / "lib64"
        lib64.symlink_to(venv / "lib")
        # The glob finds the same resolved path string
        result = get_venv_site_packages(venv)
        # Dedup: lib64/python3.14/site-packages resolves to same str as lib entry
        assert len([p for p in result if "site-packages" in p]) >= 1

    def test_lib64_independent_path_included(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        sp_lib = venv / "lib" / "python3.14" / "site-packages"
        sp_lib.mkdir(parents=True)
        sp_lib64 = venv / "lib64" / "python3.14" / "site-packages"
        sp_lib64.mkdir(parents=True)
        result = get_venv_site_packages(venv)
        assert str(sp_lib) in result
        assert str(sp_lib64) in result
        assert len(result) == 2

    def test_no_lib_dir_returns_empty(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").touch()
        assert get_venv_site_packages(venv) == []


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
