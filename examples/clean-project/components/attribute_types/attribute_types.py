"""Runtime + type-time contract test for Attribute type inference.

Uses assert_type() for static checking (ty/mypy) and records expected types
for runtime verification. The test in tests/test_attribute_types.py:
  1. Type-time: ty/mypy verify assert_type() declarations
  2. Runtime: pytest instantiates the component and checks type() matches
"""

from typing import assert_type

from batou.component import Attribute, Component


# Expected types: (conversion, default) -> (ty_type, runtime_type)
# ty_type: what the type checker infers
# runtime_type: what batou actually produces after coercion
EXPECTED_TYPES: dict[str, tuple[str, str]] = {
    # --- Clean: matching types ---
    "str_clean": ("str", "str"),
    "int_clean": ("int", "int"),
    "bool_clean": ("bool", "bool"),
    "list_clean": ("list[str]", "list"),
    "none_str": ("str", "NoneType"),  # None default, no override -> None
    # --- Mismatched: conversion != default ---
    # KEY INSIGHT: batou does NOT coerce defaults to the conversion type!
    # The default value keeps its original type. Coercion only happens
    # when values come from environment overrides (ConfigString).
    "str_int": ("str | int", "int"),  # default 42 stays int, not coerced to str
    "int_str": ("int | str", "str"),  # default "5" stays str, not coerced to int
    "list_str": ("list[str] | str", "str"),  # default "a,b,c" stays str
    "bool_int": ("int", "int"),  # default 1 stays int; ty loses bool
    "int_float": ("int | float", "float"),  # default 3.14 stays float
    "str_bytes": ("str | bytes", "bytes"),  # default b"utf-8" stays bytes
    "dict_list": ("dict[str, str] | list[str]", "list"),  # default ["a","b"] stays list
    "list_dict": ("list[str] | dict[str, str]", "dict"),  # default {"key":"val"} stays dict
    "str_none": ("str", "NoneType"),  # None default, no override -> None
    "int_none": ("int", "NoneType"),  # None default, no override -> None
}


class AttributeTypes(Component):
    # --- Basic: matching types ---
    str_clean = Attribute(str, default="hello")
    int_clean = Attribute(int, default=42)
    bool_clean = Attribute(bool, default=True)
    list_clean = Attribute(list, default=["a", "b"])
    none_str = Attribute(str, default=None)

    # --- Mismatched: conversion type != default type ---
    str_int = Attribute(str, default=42)
    int_str = Attribute(int, default="5")
    list_str = Attribute(list, default="a,b,c")
    bool_int = Attribute(bool, default=1)
    int_float = Attribute(int, default=3.14)
    str_bytes = Attribute(str, default=b"utf-8")
    dict_list = Attribute(dict, default=["a", "b"])
    list_dict = Attribute(list, default={"key": "val"})
    str_none = Attribute(str, default=None)
    int_none = Attribute(int, default=None)

    def configure(self) -> None:
        # --- Type-time assertions (ty/mypy check these) ---
        assert_type(self.str_clean, str)
        assert_type(self.int_clean, int)
        assert_type(self.bool_clean, bool)
        # ty infers list[Unknown] | list[str] for list defaults.
        # assert_type requires exact match, so we skip list_clean here
        # and rely on the runtime test for verification.
        # assert_type(self.list_clean, list[Unknown] | list[str])
        assert_type(self.none_str, str)

        # These unions are what ty actually infers for mismatched defaults.
        # If ty changes inference, these will fail at type-check time.
        assert_type(self.str_int, str | int)
        assert_type(self.int_str, int | str)
        assert_type(self.list_str, list | str)  # ty infers list[Unknown] | str
        assert_type(self.bool_int, int)  # false negative: bool <: int
        assert_type(self.int_float, int | float)
        assert_type(self.str_bytes, str | bytes)
        assert_type(self.dict_list, dict | list[str])  # ty infers dict[Unknown,Unknown] | list[str]
        assert_type(self.list_dict, list | dict[str, str])  # ty infers list[Unknown] | dict[str,str]
        assert_type(self.str_none, str)  # false negative: None lost
        assert_type(self.int_none, int)  # false negative: None lost
