from batou.component import Component

class PFADatabase(Component):
    username: str
    password: str | None
    database: str
    dbms: str
    command_prefix: str
    locale: str

    def __init__(
        self,
        *,
        username: str = ...,
        password: str | None = ...,
        database: str = ...,
        dbms: str = ...,
        command_prefix: str = ...,
        locale: str = ...,
    ) -> None: ...
    def configure(self) -> None: ...
