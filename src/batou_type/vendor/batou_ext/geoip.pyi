from batou.component import Attribute, Component, ConfigString

class GeoIPDatabase(Component):
    license_key: str | None
    download_url = Attribute(str)

    def __init__(
        self,
        *,
        download_url: str | ConfigString = ...,
        license_key: str | None = ...,
    ) -> None: ...
    def configure(self) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...
