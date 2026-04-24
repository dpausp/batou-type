from typing import Any

from batou import ReportingException
from batou.component import Attribute, Component
from batou.environment import Environment
from batou.host import Host
from batou.lib.cron import InstallCrontab as CronInstallCrontab
from batou.lib.file import File, ManagedContentBase
from batou.utils import Address, NetLoc

def rebuild(cls: type) -> type: ...
def nix_dict_to_nix(dct: dict[str, str]) -> str: ...
def seq_to_nix(seq: tuple[Any, ...] | list[Any]) -> str: ...
def mapping_to_nix(obj: dict[str, Any]) -> str: ...
def str_to_nix(value: str) -> str: ...
def environment_to_nix_dict(env: Environment) -> dict[str, str]: ...
def netloc_to_nix_dict(netloc: NetLoc) -> dict[str, str]: ...
def address_to_nix_dict(addr: Address) -> dict[str, str]: ...
def host_to_nix_dict(host: Host) -> dict[str, str]: ...
def value_to_nix(value: Any) -> str | None: ...
def component_to_nix(component: Component) -> str: ...

class Package(Component):
    package: str | None
    attribute: str | None
    file: str | None

    def __init__(
        self,
        package: str | None = ...,
        *,
        attribute: str | None = ...,
        file: str | None = ...,
    ) -> None: ...
    def configure(self) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...
    @property
    def namevar_for_breadcrumb(self) -> str | None: ...

class PurgePackage(Component):
    namevar: str
    package: str | None

    def __init__(
        self,
        package: str | None = ...,
    ) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...

class UserEnv(Component):
    namevar: str
    profile_name: str | None
    channel = Attribute(str)
    ignore_collisions: bool
    shellInit: str
    packages: tuple[str, ...]
    let_extra: str

    def __init__(
        self,
        profile_name: str | None = ...,
        *,
        channel: str = ...,
        ignore_collisions: bool = ...,
        shellInit: str = ...,
        packages: tuple[str, ...] = ...,
        let_extra: str = ...,
    ) -> None: ...
    def configure(self) -> None: ...

class Rebuild(Component):
    dependencies: Any | None
    continue_on_warning: bool

    def __init__(
        self,
        *,
        dependencies: Any | None = ...,
        continue_on_warning: bool = ...,
    ) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...

class UserInit(Component):
    def configure(self) -> None: ...
    @property
    def env(self) -> dict[str, str]: ...
    def start(self) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...

class FixSupervisorStartedBySystemd(Component):
    def verify(self) -> None: ...
    def update(self) -> None: ...

class InstallCrontab(CronInstallCrontab):
    def update(self) -> None: ...

class SensuChecks(Component):
    purge_old_batou_json: bool

    def __init__(
        self,
        *,
        purge_old_batou_json: bool = ...,
    ) -> None: ...
    def configure(self) -> None: ...

class LogrotateIntegration(Component):
    def configure(self) -> None: ...

class PythonWithNixPackages(Component):
    python: str | None
    nix_packages: tuple[str, ...]
    pythonPackages: Any | None

    def __init__(
        self,
        *,
        python: str | None = ...,
        nix_packages: tuple[str, ...] = ...,
        pythonPackages: Any | None = ...,
    ) -> None: ...
    def configure(self) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...

class NixSyntaxCheckFailed(ReportingException):
    error_msg: str
    path: str | None

    def __init__(self, error_msg: str, path: str | None = None) -> None: ...
    def report(self) -> None: ...

class NixContent(ManagedContentBase):
    format_nix_code: bool
    check_nix_syntax: bool

    def render(self) -> None: ...
    def verify(self, predicting: bool = ...) -> None: ...

class NixFile(File):
    format_nix_code: bool

    def configure(self) -> None: ...
