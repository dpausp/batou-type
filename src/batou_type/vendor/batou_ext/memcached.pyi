from batou.component import Attribute, Component

class Memcached(Component):
    port = Attribute(int)
    custom_config: dict[str, str]

    def __init__(
        self,
        *,
        port: int = ...,
        custom_config: dict[str, str] = ...,
    ) -> None: ...
    def configure(self) -> None: ...
