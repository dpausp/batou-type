"""BUG: Attribute declared as one type but default value is a different type.

The key pathology: batou converts defaults to the declared type at component
instantiation, so the value may be coerced. But some code paths use the
attribute *before* conversion or assume the original type of the default.
This creates inconsistent behavior depending on where the attribute is accessed.
"""

from batou.component import Attribute, Component
from batou.lib.file import File


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

    def configure(self):
        # USE AS STR: correct per declaration
        # This works because batou converts 42 -> "42"
        upper_port = self.port.upper()

        # USE AS INT: wrong per declaration but matches default type
        # Will crash at runtime because port is now "42" (a string)
        next_port = self.port + 1

        # USE AS INT: correct per declaration
        # batou converts "5" -> 5
        doubled = self.count * 2

        # USE AS STR: wrong per declaration but matches default type
        # Will crash because count is now 5 (an int), not "5"
        label = "count=" + self.count

        # USE AS LIST: correct per declaration
        # batou converts "a,b,c" -> ["a,b,c"] (one element!)
        first_item = self.items[0]

        # USE AS STR: wrong per declaration but matches default type
        # Will crash because items is now a list, not "a,b,c"
        split = self.items.split(",")

        # USE AS BOOL: correct per declaration
        # batou converts 1 -> True
        if self.enabled:
            pass

        # USE AS INT: wrong per declaration but matches default type
        # bool is subclass of int in Python, so this "works" but is wrong
        flags = self.enabled + 1

        # PASS TO API expecting str: works after coercion
        self += File("port.txt", content=self.port)

        # PASS TO API expecting int: crashes after coercion
        self += File("count.txt", content=self.count)
