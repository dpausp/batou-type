"""reveal_type probes for Attribute type inference.

Run:  ty check components/reveal_types/reveal_types.py --extra-search-path <stubs>
Run:  mypy components/reveal_types/reveal_types.py --explicit-package-bases
"""

from batou.component import Attribute, Component
from batou.lib.file import File
from batou.utils import Address


class RevealTypes(Component):
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

    # --- Usage contexts ---
    def configure(self) -> None:
        reveal_type(self.str_clean)
        reveal_type(self.int_clean)
        reveal_type(self.bool_clean)
        reveal_type(self.list_clean)
        reveal_type(self.none_str)

        reveal_type(self.str_int)
        reveal_type(self.int_str)
        reveal_type(self.list_str)
        reveal_type(self.bool_int)
        reveal_type(self.int_float)
        reveal_type(self.str_bytes)
        reveal_type(self.dict_list)
        reveal_type(self.list_dict)
        reveal_type(self.str_none)
        reveal_type(self.int_none)

        # Arithmetic on mismatched attributes
        reveal_type(self.str_int + 1)
        reveal_type(self.int_str * 2)
        reveal_type("prefix-" + self.int_str)

        # Method calls on mismatched attributes
        reveal_type(self.str_int.upper())
        reveal_type(self.list_str.split(","))
        reveal_type(self.dict_list.get("key"))
        reveal_type(self.str_bytes.decode("utf-8"))

        # Pass to constructors
        reveal_type(Address(self.str_int, 8080))
        reveal_type(File("x.txt", content=self.int_str))
        reveal_type(File("x.txt", content=self.str_int))
