from batou.component import Attribute, Component

class HTTPBasicAuth(Component):
    env_name: str | None
    fcio_auth: bool
    username: str | None
    password: str | None
    basic_auth_string: str | None
    providing: bool

    def __init__(
        self,
        *,
        fcio_auth: bool = ...,
        providing: bool = ...,
        env_name: str | None = ...,
        username: str | None = ...,
        password: str | None = ...,
        basic_auth_string: str | None = ...,
    ) -> None: ...
    def configure(self) -> None: ...

class HTTPServiceWatchdog(Component):
    namevar: str
    predefined_service: bool
    watchdog_script_path = Attribute(str)
    script = Attribute(str)
    healthcheck_url = Attribute(str)
    healthcheck_timeout = Attribute(int)
    check_interval = Attribute(int)
    startup_check_interval = Attribute(int)
    start_timeout = Attribute(int)
    watchdog_interval = Attribute(int)
    rebuild: bool

    def __init__(
        self,
        service: str | None = ...,
        *,
        predefined_service: bool = ...,
        watchdog_script_path: str = ...,
        script: str | None = ...,
        healthcheck_url: str = ...,
        healthcheck_timeout: int = ...,
        check_interval: int = ...,
        startup_check_interval: int = ...,
        start_timeout: int = ...,
        watchdog_interval: int = ...,
        rebuild: bool = ...,
    ) -> None: ...
    def configure(self) -> None: ...

class HTTPWatchdogScript(Component):
    def configure(self) -> None: ...
