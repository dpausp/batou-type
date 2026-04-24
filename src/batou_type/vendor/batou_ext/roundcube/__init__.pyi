from batou.component import Attribute, Component, ConfigString
from batou.utils import Address

class Roundcube(Component):
    release: str
    checksum: str  # type: ignore[assignment]
    address = Attribute(Address)
    skin: str
    support_url: str
    smtp_user: str
    smtp_pass: str
    config: str

    def __init__(
        self,
        *,
        address: str | Address | ConfigString = ...,
        release: str = ...,
        checksum: str = ...,
        skin: str = ...,
        support_url: str = ...,
        smtp_user: str = ...,
        smtp_pass: str = ...,
        config: str = ...,
    ) -> None: ...
    def configure(self) -> None: ...

class RoundcubeInit(Component):
    namevar: str

    def __init__(
        self,
        roundcube: str | None = ...,
    ) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...
