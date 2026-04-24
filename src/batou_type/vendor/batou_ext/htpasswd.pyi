from batou.component import Component

class HTPasswd(Component):
    namevar: str
    users: str

    def __init__(
        self,
        path: str | None = ...,
        *,
        users: str = ...,
    ) -> None: ...
    def configure(self) -> None: ...
