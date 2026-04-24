from batou.component import Attribute, Component

class Mirror(Component):
    public_name: str | None
    base = Attribute(str)
    protocol = Attribute(str)
    nginx_enable: bool
    nginx_config_path: str | None
    nginx_docroot: str | None
    nginx_reload_command = Attribute(str)
    provide_itself: bool
    credentials: str | None
    authstring: str | None
    use_letsencrypt: bool

    def __init__(
        self,
        *,
        base: str = ...,
        protocol: str = ...,
        nginx_enable: bool = ...,
        nginx_reload_command: str = ...,
        provide_itself: bool = ...,
        use_letsencrypt: bool = ...,
        public_name: str | None = ...,
        nginx_config_path: str | None = ...,
        nginx_docroot: str | None = ...,
        credentials: str | None = ...,
        authstring: str | None = ...,
    ) -> None: ...
    def configure(self) -> None: ...
    def url(self, path: str) -> str: ...
