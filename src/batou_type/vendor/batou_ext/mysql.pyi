from batou.component import Attribute, Component

class MySQLGeneric(Component):
    namevar: str
    database: str | None
    username: str | None
    password: str | None
    admin_password: str | None
    provide_as = Attribute(str)
    port = Attribute(int)
    allow_from_hostname = Attribute(str)

    def __init__(
        self,
        database: str | None = ...,
        *,
        provide_as: str = ...,
        port: int = ...,
        allow_from_hostname: str = ...,
        username: str | None = ...,
        password: str | None = ...,
        admin_password: str | None = ...,
    ) -> None: ...
    def configure(self) -> None: ...
