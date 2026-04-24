"""BUG: Address(connect_address) expects str, gets int 42."""

from batou.component import Component
from batou.utils import Address


class BadAddress(Component):
    def configure(self):
        # BUG: connect_address should be str, not int
        self.addr = Address(42, 8080)
