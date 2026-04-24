from batou.component import Attribute, Component

class SSHKeyPair(Component):
    id_rsa: str | None
    id_rsa_pub: str | None
    id_ed25519: str | None
    id_ed25519_pub: str | None
    file_name = Attribute(str)
    scan_hosts: list[str]
    provide_itself: bool
    purge_unmanaged_keys: bool
    provide_as = Attribute(str)

    def __init__(
        self,
        *,
        file_name: str | None = ...,
        scan_hosts: list[str] = ...,
        provide_itself: bool = ...,
        purge_unmanaged_keys: bool = ...,
        provide_as: str = ...,
        id_rsa: str | None = ...,
        id_rsa_pub: str | None = ...,
        id_ed25519: str | None = ...,
        id_ed25519_pub: str | None = ...,
    ) -> None: ...

class ScanHost(Component):
    namevar: str
    hostname: str | None
    known_hosts: str
    port: int

    def __init__(
        self,
        hostname: str | None = ...,
        *,
        known_hosts: str = ...,
        port: int = ...,
    ) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...
