from batou.component import Attribute, Component

class Certificate(Component):
    namevar: str
    domain: str | None
    dehydrated_publickey_algo = Attribute(str)
    extracommand: str | None
    alternative_names: tuple[str, ...] | list[str]
    wellknown: str | None
    docroot: str | None
    refresh_timing: str | None
    key_content: str | None
    crt_content: str | None
    trusted_crt_content: str | None
    use_letsencrypt: bool
    letsencrypt_ca: str
    letsencrypt_challenge: str
    letsencrypt_hook: str
    letsencrypt_alternative_chain: str | None
    enable_check: bool
    granted_user = Attribute(str)
    key: str
    fullchain: str

    def __init__(
        self,
        domain: str | None = ...,
        *,
        alternative_names: tuple[str, ...] | list[str] = ...,
        wellknown: str | None = ...,
        docroot: str | None = ...,
        key_content: str | None = ...,
        crt_content: str | None = ...,
        trusted_crt_content: str | None = ...,
        extracommand: str | None = ...,
        refresh_timing: str | None = ...,
        letsencrypt_ca: str = ...,
        letsencrypt_challenge: str = ...,
        letsencrypt_hook: str = ...,
        letsencrypt_alternative_chain: str | None = ...,
        dehydrated_publickey_algo: str = ...,
        use_letsencrypt: bool = ...,
        enable_check: bool = ...,
        granted_user: str = ...,
    ) -> None: ...
    def configure(self) -> None: ...
    def activate_letsencrypt(self) -> ActivateLetsEncrypt: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...

class ActivateLetsEncrypt(Component):
    cert: Certificate | None

    def verify(self) -> None: ...
    def update(self) -> None: ...
    @property
    def namevar_for_breadcrumb(self) -> str | None: ...

class CertificateCheck(Component):
    namevar: str
    public_name: str | None
    port = Attribute(int)
    warning_days: int
    critical_days: int

    def __init__(
        self,
        public_name: str | None = ...,
        *,
        port: int = ...,
        warning_days: int = ...,
        critical_days: int = ...,
    ) -> None: ...
    def configure(self) -> None: ...

class CertificateCheckLocal(Component):
    namevar: str
    certificate_path: str | None
    name: str | None
    warning_days: int
    critical_days: int

    def __init__(
        self,
        certificate_path: str | None = ...,
        *,
        name: str | None = ...,
        warning_days: int = ...,
        critical_days: int = ...,
    ) -> None: ...
    def configure(self) -> None: ...
