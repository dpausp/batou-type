from typing import Any

from batou.component import Attribute, Component

class PostgresServer(Component):
    listen_port: str

    def __init__(
        self,
        *,
        listen_port: str = ...,
    ) -> None: ...
    def configure(self) -> None: ...

class PostgresDataComponent(Component):
    command_prefix = Attribute(str)

    def __init__(
        self,
        *,
        command_prefix: str = ...,
    ) -> None: ...
    def configure(self) -> None: ...
    def pgcmd(self, cmd: str, *args: str, **kw: Any) -> tuple[str, str]: ...

class DB(PostgresDataComponent):
    namevar: str
    db: str
    command_prefix = Attribute(str)
    locale: str  # type: ignore[assignment]
    template: str  # type: ignore[assignment]
    owner: str | None

    def __init__(
        self,
        db: str = ...,
        *,
        command_prefix: str = ...,
        locale: str = ...,
        template: str = ...,
        owner: str | None = ...,
    ) -> None: ...
    def configure(self) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...

class User(PostgresDataComponent):
    namevar: str
    name: str | None
    command_prefix = Attribute(str)
    flags: str
    password: str | None

    def __init__(
        self,
        name: str | None = ...,
        *,
        command_prefix: str = ...,
        flags: str = ...,
        password: str | None = ...,
    ) -> None: ...
    def configure(self) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...

class Extension(PostgresDataComponent):
    namevar: str
    extension_name: str | None
    command_prefix = Attribute(str)
    db: str

    def __init__(
        self,
        extension_name: str | None = ...,
        *,
        command_prefix: str = ...,
        db: str = ...,
    ) -> None: ...
    def configure(self) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...

class Grant(PostgresDataComponent):
    namevar: str
    user: str | None
    command_prefix = Attribute(str)
    table_permissions: list[str]
    schema_permissions: list[str]
    db: str
    schema: str

    def __init__(
        self,
        user: str | None = ...,
        *,
        command_prefix: str = ...,
        table_permissions: list[str] = ...,
        schema_permissions: list[str] = ...,
        db: str = ...,
        schema: str = ...,
    ) -> None: ...
    def configure(self) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...
