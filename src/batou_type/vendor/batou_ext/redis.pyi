from batou.component import Attribute, Component

class Redis(Component):
    db = Attribute(int)
    cleanup: bool
    cleanup_command = Attribute(str)
    provide_as = Attribute(str)
    password: str | None
    password_file: str
    port: int

    def __init__(
        self,
        *,
        db: int = ...,
        cleanup: bool = ...,
        cleanup_command: str = ...,
        provide_as: str = ...,
        password: str | None = ...,
        password_file: str = ...,
        port: int = ...,
    ) -> None: ...
    def configure(self) -> None: ...
    def resource(self, filename: str) -> str: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...
