"""Runtime + type-time contract test for Attribute type inference.

Type-time:  ty/mypy verify assert_type() in attribute_types.py
Runtime:    pytest instantiates AttributeTypes and checks type() matches expected
"""
import os
import sys
from pathlib import Path
from types import NoneType

import pytest

from batou.component import ComponentDefinition
from batou.environment import Environment
from batou.host import Host

# Example project uses hyphenated directory name — add to sys.path for import
_example_project = Path(__file__).resolve().parent.parent.parent / "examples" / "clean-project"
sys.path.insert(0, str(_example_project))

from components.attribute_types.attribute_types import (  # noqa: E402  # ty: ignore[unresolved-import]
    EXPECTED_TYPES,
    AttributeTypes,
)


@pytest.fixture
def component(tmp_path: Path) -> AttributeTypes:
    """Create and prepare an AttributeTypes component via batou infrastructure."""
    os.chdir(str(tmp_path))
    environment = Environment("test", basedir=str(tmp_path))
    environment._set_defaults()

    compdef = ComponentDefinition(AttributeTypes)
    compdef.defdir = str(tmp_path)
    environment.components[compdef.name] = compdef
    environment.hosts["localhost"] = host = Host("localhost", environment)
    root = environment.add_root(compdef.name, host)
    root.prepare()
    root.component.deploy()
    return root.component


def test_clean_types_match_declaration(component: AttributeTypes) -> None:
    """Matching conversion+default should produce the declared type."""
    assert type(component.str_clean) is str
    assert type(component.int_clean) is int
    assert type(component.bool_clean) is bool
    assert type(component.list_clean) is list
    assert type(component.none_str) is NoneType


def test_mismatched_types_are_coerced(component: AttributeTypes) -> None:
    """Mismatched defaults keep their original type — batou does NOT coerce defaults.

    Coercion only applies to values from environment overrides (ConfigString).
    This is the core insight: the conversion type is a lie for defaults.
    """
    # Attribute(str, default=42) -> stays int 42, NOT "42"
    assert type(component.str_int) is int
    assert component.str_int == 42

    # Attribute(int, default="5") -> stays str "5", NOT 5
    assert type(component.int_str) is str
    assert component.int_str == "5"

    # Attribute(list, default="a,b,c") -> stays str "a,b,c", NOT ["a,b,c"]
    assert type(component.list_str) is str
    assert component.list_str == "a,b,c"

    # Attribute(bool, default=1) -> stays int 1, NOT True
    assert type(component.bool_int) is int
    assert component.bool_int == 1

    # Attribute(int, default=3.14) -> stays float 3.14, NOT 3
    assert type(component.int_float) is float
    assert component.int_float == 3.14


def test_none_defaults_stay_none(component: AttributeTypes) -> None:
    """None defaults without override remain None at runtime."""
    assert component.str_none is None
    assert component.int_none is None
    assert component.none_str is None


def test_expected_types_table_is_complete() -> None:
    """Every attribute with EXPECTED_TYPES entry actually exists."""
    for attr_name in EXPECTED_TYPES:
        assert hasattr(AttributeTypes, attr_name), f"missing attribute: {attr_name}"


def test_runtime_matches_expected(component: AttributeTypes) -> None:
    """Cross-check runtime types against the EXPECTED_TYPES table."""
    mismatches: list[str] = []
    for attr_name, (ty_type, expected_runtime) in EXPECTED_TYPES.items():
        actual = type(getattr(component, attr_name))
        expected = {
            "str": str,
            "int": int,
            "bool": bool,
            "list": list,
            "dict": dict,
            "float": float,
            "bytes": bytes,
            "NoneType": NoneType,
        }[expected_runtime]
        if actual is not expected:
            mismatches.append(
                f"  {attr_name}: expected {expected.__name__}, got {actual.__name__}"
            )
    if mismatches:
        pytest.fail("Runtime type mismatches:\n" + "\n".join(mismatches))
