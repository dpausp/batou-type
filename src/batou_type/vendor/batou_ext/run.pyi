from batou.component import Component

class Run(Component):
    namevar: str
    command: str | None
    content: str | None
    file: str | None
    env: dict[str, str] | None

    def __init__(
        self,
        command: str | None = ...,
        *,
        content: str | None = ...,
        file: str | None = ...,
        env: dict[str, str] | None = ...,
    ) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...
