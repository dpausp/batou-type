"""Batou type checking plugin for pytest."""

from pathlib import Path

import pytest

from batou_type.core import Checker, check_all

_BATOU_TY_RESULTS_STASH_KEY = pytest.StashKey[dict[str, bool]]()
_BATOU_TY_OUTPUT_STASH_KEY = pytest.StashKey[dict[str, str]]()


class BatouComponentItem(pytest.Item):
    """Type checking result for a single component file."""

    name = "batou_ty"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_marker(self.name)

    def runtest(self) -> None:
        error_results = self.config.stash.get(_BATOU_TY_RESULTS_STASH_KEY, {})
        output_results = self.config.stash.get(_BATOU_TY_OUTPUT_STASH_KEY, {})

        file_key = str(self.path.relative_to(self.config.rootpath))
        has_errors = error_results.get(file_key, False)
        output = output_results.get(file_key, "")

        if has_errors and output.strip():
            # Get diagnostic count from "Found X diagnostics"
            import re

            match = re.search(r"Found (\d+) diagnostic", output)
            if match:
                count = match.group(1)
                msg = f"Type check failed with {count} error(s)"
            else:
                msg = "Type check failed"

            pytest.fail(msg + "\n" + output.strip())


class BatouComponentFile(pytest.File):
    """A batou component Python file."""

    def collect(self) -> list[BatouComponentItem]:
        return [BatouComponentItem.from_parent(self, name=BatouComponentItem.name)]


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("batou")
    group.addoption(
        "--batou-ty",
        action="store_true",
        help="Run type checking with ty on batou components",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "batou_ty: Tests which run batou type checking.")


def pytest_collect_file(
    file_path: Path, parent: pytest.Collector
) -> BatouComponentFile | None:
    config = parent.config
    if not config.option.batou_ty:
        return None

    # Collect only components/**/*.py files
    if file_path.suffix != ".py":
        return None
    if "components" not in file_path.parts:
        return None

    return BatouComponentFile.from_parent(parent, path=file_path)


def pytest_collection_modifyitems(
    session: pytest.Session, items: list[pytest.Item]
) -> None:
    config = session.config
    if not config.option.batou_ty:
        return

    # Check if we already collected results
    if config.stash.get(_BATOU_TY_RESULTS_STASH_KEY, None):
        return

    # Run all type checks upfront (collect phase)
    root = config.rootpath
    results = check_all(root, [Checker.ty])

    # Store results in stash for test items to access
    error_results = {r.path: r.has_errors for r in results}
    output_results = {r.path: r.output for r in results}

    config.stash[_BATOU_TY_RESULTS_STASH_KEY] = error_results
    config.stash[_BATOU_TY_OUTPUT_STASH_KEY] = output_results
