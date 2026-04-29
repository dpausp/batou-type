"""BUG: Attribute declared as one type but default value is a different type.

The key pathology: batou converts defaults to the declared type at component
instantiation, so the value may be coerced. But some code paths use the
attribute *before* conversion or assume the original type of the default.
This creates inconsistent behavior depending on where the attribute is accessed.
"""

from batou.component import Attribute, Component
from batou.lib.file import File
from batou.utils import Address


class DualUsage(Component):
    # Declared str, default is int — batou coerces 42 to "42"
    # But code may assume either type depending on the code path
    port = Attribute(str, default=42)

    # Declared int, default is str — batou coerces "5" to 5
    # But code may assume either type
    count = Attribute(int, default="5")

    # Declared list, default is str — batou coerces "a,b,c" to ["a,b,c"]
    # Code using it as list and as str simultaneously
    items = Attribute(list, default="a,b,c")

    # Declared bool, default is int — batou coerces 1 to True
    # Code uses it as both bool and int
    enabled = Attribute(bool, default=1)

    # Declared int, default is float — batou coerces 3.14 to int(3.14) = 3
    # Code assumes float precision
    rate = Attribute(int, default=3.14)

    # Declared str, default is bytes — bytes is not str
    encoding = Attribute(str, default=b"utf-8")

    # Declared dict, default is list — completely wrong container type
    config = Attribute(dict, default=["a", "b"])

    def configure(self):
        # USE AS STR: correct per declaration
        # This works because batou converts 42 -> "42"
        self.port.upper()

        # USE AS INT: wrong per declaration but matches default type
        # Will crash at runtime because port is now "42" (a string)
        self.port + 1

        # USE AS INT: correct per declaration
        # batou converts "5" -> 5
        self.count * 2

        # USE AS STR: wrong per declaration but matches default type
        # Will crash because count is now 5 (an int), not "5"
        "count=" + self.count

        # USE AS LIST: correct per declaration
        # batou converts "a,b,c" -> ["a,b,c"] (one element!)
        self.items[0]

        # USE AS STR: wrong per declaration but matches default type
        # Will crash because items is now a list, not "a,b,c"
        self.items.split(",")

        # USE AS BOOL: correct per declaration
        # batou converts 1 -> True
        if self.enabled:
            pass

        # USE AS INT: wrong per declaration but matches default type
        # bool is subclass of int in Python, so this "works" but is wrong
        self.enabled + 1

        # PASS TO API expecting str: works after coercion
        self += File("port.txt", content=self.port)

        # PASS TO API expecting int: crashes after coercion
        self += File("count.txt", content=self.count)

        # FLOAT USAGE: code assumes float but got int after coercion
        # int(3.14) = 3 — silently loses precision
        self.rate / 3.0  # type: ignore[unused]
        # But code treating it as float for string formatting

        # BYTES USAGE: code assumes bytes methods
        self.encoding.decode("utf-8")

        # DICT USAGE: code assumes dict methods on list
        self.config["key"]

        # PASS TO CONSTRUCTOR: str attribute passed to Address (expects str)
        # Works when default is used (int gets coerced to str)
        # But type checker sees str | int, Address wants str
        self.addr = Address(self.port, 8080)

        # PASS TO CONSTRUCTOR: int attribute used as string for content
        # int gets coerced to str, but type checker sees int | str
        self += File("rate.txt", content=self.rate)
