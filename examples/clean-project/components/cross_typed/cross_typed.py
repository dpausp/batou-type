"""Cross-component type mismatch — known blind spot for static checkers.

Static type checkers CANNOT catch these bugs because the type mismatch only
appears at runtime when one component overrides another's attributes via the
batou environment. Each component individually has correct types; the bug is
in the interaction between components.

This component documents the limits of what type checking can verify.
"""

from batou.component import Attribute, Component
from batou.lib.file import File
from batou.utils import Address


class Producer(Component):
    # Produces a string but downstream expects int
    port = Attribute(str, default="8080")

    # Produces an int but downstream expects str
    host = Attribute(int, default=42)

    # Produces a list but downstream expects str
    tags = Attribute(list, default=["web", "app"])

    # Produces None but downstream expects str
    secret = Attribute(str, default=None)

    def configure(self):
        # Producer uses its own attributes "correctly" per declaration
        _upper = self.port.upper()  # type: ignore[unused]
        _doubled = self.host * 2  # type: ignore[unused]
        _first = self.tags[0]  # type: ignore[unused]


class Consumer(Component):
    # Declared as int but receives str from Producer
    port = Attribute(int, default=8080)

    # Declared as str but receives int from Producer
    host = Attribute(str, default="localhost")

    # Declared as str but receives list from Producer
    tags = Attribute(str, default="")

    # Declared as str, default is None — Union type
    secret = Attribute(str, default=None)

    def configure(self):
        # BUG: int attribute used in arithmetic — correct per declaration
        # but at runtime may receive a string from override
        next_port = self.port + 1

        # BUG: str attribute used in string ops — correct per declaration
        # but at runtime may receive an int from override
        greeting = f"host: {self.host}"

        # BUG: str attribute used as string — correct per declaration
        # but at runtime may receive a list from override
        _split = self.tags.split(",")  # type: ignore[unused]

        # BUG: None used in string operation — works when overridden
        # but crashes when default (None) is used
        _safe = self.secret.upper()  # type: ignore[unused]

        # BUG: passing potentially-None attribute to File
        self += File("secret.txt", content=self.secret)

        # BUG: passing str attribute to Address port (expects int)
        # Works when default 8080 is used, crashes when overridden with str
        self.addr = Address("example.com", self.port)

        # BUG: passing int attribute to File content (expects str)
        # Works when default "localhost" is used, crashes when overridden with int
        self += File("host.txt", content=self.host)
