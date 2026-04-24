from batou.component import Component

class ErlangCookie(Component):
    path: str
    cookie: str | None

    def __init__(
        self,
        *,
        path: str = ...,
        cookie: str | None = ...,
    ) -> None: ...
    def configure(self) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...

class VHost(Component):
    namevar: str
    name: str | None

    def __init__(
        self,
        name: str | None = ...,
    ) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...

class Permissions(Component):
    namevar: str
    username: str | None
    permissions: dict[str, str] | None

    def __init__(
        self,
        username: str | None = ...,
        *,
        permissions: dict[str, str] | None = ...,
    ) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...

class User(Component):
    namevar: str
    username: str | None
    password: str | None
    tags: list[str] | None

    def __init__(
        self,
        username: str | None = ...,
        *,
        password: str | None = ...,
        tags: list[str] | None = ...,
    ) -> None: ...
    def configure(self) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...

class PurgeUser(Component):
    namevar: str
    username: str | None

    def __init__(
        self,
        username: str | None = ...,
    ) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...
