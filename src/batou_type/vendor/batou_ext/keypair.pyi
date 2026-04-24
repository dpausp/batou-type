from batou.component import Attribute, Component

class KeyPair(Component):
    namevar: str
    crt: str | None
    key: str | None
    base_path = Attribute(str)
    provide_itself = Attribute(bool)

    def __init__(
        self,
        name: str | None = ...,
        *,
        base_path: str = ...,
        provide_itself: bool = ...,
        crt: str | None = ...,
        key: str | None = ...,
    ) -> None: ...
    def configure(self) -> None: ...
