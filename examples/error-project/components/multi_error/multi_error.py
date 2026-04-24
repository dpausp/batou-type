"""BUG: Multiple errors — wrong Address args + wrong File content + calling nonexistent method."""

from batou.component import Component
from batou.lib.file import File
from batou.utils import Address


class MultiError(Component):
    def configure(self):
        # BUG 1: Address expects str, gets list
        self.addr = Address(["not", "a", "string"], "not_a_port")

        # BUG 2: File content expects str, gets list
        self += File("broken.txt", content=[1, 2, 3])

        # BUG 3: nonexistent method on Component
        self.totally_bogus_call()
