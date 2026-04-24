from batou.component import Attribute, Component

class PostfixRelay(Component):
    smtp_relay_host = Attribute(str)
    smtp_relay_port = Attribute(int)
    smtp_tls: bool
    smtp_auth: bool
    smtp_user = Attribute(str)
    smtp_password = Attribute(str)
    provide_as: str | None

    def __init__(
        self,
        *,
        smtp_relay_host: str = ...,
        smtp_relay_port: int = ...,
        smtp_tls: bool = ...,
        smtp_auth: bool = ...,
        smtp_user: str = ...,
        smtp_password: str = ...,
        provide_as: str | None = ...,
    ) -> None: ...
    def configure(self) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...

class Mailhog(Component):
    public_name = Attribute(str)
    public_smtp_name = Attribute(str)
    mailport = Attribute(int)
    uiport = Attribute(int)
    apiport = Attribute(int)
    purge_old_mailhog_configs: bool
    http_auth_enable: bool
    http_basic_auth: Component | None
    systemd_namespace = Attribute(str)
    disable_stdout: bool
    storage_engine = Attribute(str)
    provide_as: str | None

    def __init__(
        self,
        *,
        public_name: str = ...,
        public_smtp_name: str | None = ...,
        mailport: int = ...,
        uiport: int = ...,
        apiport: int = ...,
        purge_old_mailhog_configs: bool = ...,
        http_auth_enable: bool = ...,
        systemd_namespace: str = ...,
        disable_stdout: bool = ...,
        storage_engine: str = ...,
        http_basic_auth: Component | None = ...,
        provide_as: str | None = ...,
    ) -> None: ...
    def configure(self) -> None: ...

class Mailpit(Component):
    public_name = Attribute(str)
    public_smtp_name = Attribute(str)
    ui_port = Attribute(int)
    smtp_port = Attribute(int)
    max = Attribute(int)
    http_basic_auth: Component | None
    provide_as: str | None

    def __init__(
        self,
        *,
        public_name: str = ...,
        public_smtp_name: str | None = ...,
        ui_port: int = ...,
        smtp_port: int = ...,
        max: int = ...,  # noqa: A002
        http_basic_auth: Component | None = ...,
        provide_as: str | None = ...,
    ) -> None: ...
    def configure(self) -> None: ...
