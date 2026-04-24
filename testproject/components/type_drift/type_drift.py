"""BUG: Attribute used as one type in configure() and a different type in verify/update."""

from batou.component import Attribute, Component
from batou.lib.file import File


class TypeDrift(Component):
    # Declared as str but used as both str and int
    port = Attribute(str, default="8080")

    # Declared as list but used as dict in one place
    settings = Attribute(list, default=[])

    # Declared as int but used as str (string concatenation)
    count = Attribute(int, default=5)

    def configure(self):
        # BUG: treating str attribute as int
        port_num = int(self.port) + 1

        # BUG: treating list attribute as dict
        value = self.settings.get("key", "fallback")

        # BUG: using int attribute in string concatenation without str()
        label = "count-" + self.count

        # BUG: passing attribute to File content expecting str,
        # but count is declared int — works via implicit str conversion
        self += File("count.txt", content=self.count)

        # BUG: using port (str) in arithmetic comparison as if it were int
        if self.port > 1024:
            pass

        # BUG: passing list where str expected
        self += File("settings.txt", content=self.settings)
