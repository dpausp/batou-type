from batou.component import Attribute, Component, ConfigString
from batou.utils import Address

class PFA(Component):
    release: str
    checksum: str  # type: ignore[assignment]
    address = Attribute(Address)
    admin_password: str | None
    salt: str
    config: str

    def __init__(
        self,
        *,
        address: str | Address | ConfigString = ...,
        release: str = ...,
        checksum: str = ...,
        admin_password: str | None = ...,
        salt: str = ...,
        config: str = ...,
    ) -> None: ...
    def configure(self) -> None: ...
    @property
    def admin_password_encrypted(self) -> str: ...
