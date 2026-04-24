"""BUG: Attribute(str, default=42) — default type doesn't match conversion."""

from batou.component import Attribute, Component


class BadDefault(Component):
    # BUG: default is int but conversion is str
    name = Attribute(str, default=42)

    def configure(self):
        pass
