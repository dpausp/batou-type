from batou.component import Attribute, Component, ConfigString
from batou.utils import Address

def resolve_v6(address: Address) -> str: ...

class PFAPostfix(Component):
    address = Attribute(Address)

    def __init__(
        self,
        *,
        address: str | Address | ConfigString = ...,
    ) -> None: ...
    def configure(self) -> None: ...
