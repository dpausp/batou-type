from batou.component import Component

class Ini(Component):
    extensions: tuple[str, ...]
    settings: str
    logs: str | None

    def __init__(
        self,
        *,
        extensions: tuple[str, ...] = ...,
        settings: str = ...,
        logs: str | None = ...,
    ) -> None: ...
    def configure(self) -> None: ...

class FPM(Component):
    namevar: str
    name: str | None
    keep_env: bool
    php_ini: str | None
    logs: str | None
    global_settings: str
    pool_settings: str
    port: int
    env: dict[str, str]
    dependency_strings: tuple[str, ...]

    def __init__(
        self,
        name: str | None = ...,
        *,
        keep_env: bool = ...,
        php_ini: str | None = ...,
        logs: str | None = ...,
        global_settings: str = ...,
        pool_settings: str = ...,
        port: int = ...,
        env: dict[str, str] = ...,
        dependency_strings: tuple[str, ...] = ...,
    ) -> None: ...
    def configure(self) -> None: ...
