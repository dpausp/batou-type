"""BUGS that are likely false negatives — checker probably won't catch these."""

from batou.component import Attribute, Component
from batou.lib.file import File
from batou.utils import Address


class SilentBugs(Component):
    fqdn = Attribute(str)
    port = Attribute(int, default=8080)

    def configure(self):
        self.address: Address = Address(self.fqdn, self.port)

        # BUG: wrong return type — Address.connect is NetLoc, assigning to str-typed var
        # Likely false negative: checkers may not catch this
        self.host_str: str = self.address.connect

        # BUG: passing bool where int expected for port
        # Likely false negative: int/bool subtype relationship
        self.other_addr = Address("other.example.com", True)

        # BUG: sensitive_data expects bool, passing string "yes"
        # Likely false negative: literal checking may not catch this
        self += File("secret.txt", content="data", sensitive_data="yes")
