from typing import Any
from xmlrpc.client import ServerProxy

from batou.component import Attribute, Component
from batou.environment import Environment

def create_xmlrpc_client(environment: Environment) -> ServerProxy: ...
def change_maintenance_state(
    xmlrpc: ServerProxy,
    rg_name: str,
    desired_state: bool,
    predict_only: bool = ...,
) -> None: ...

class DNSAliases(Component):
    postfix: str
    project: str | None
    api_key: str | None
    wait_for_aliases = Attribute(int)

    def __init__(
        self,
        *,
        wait_for_aliases: int = ...,
        postfix: str = ...,
        project: str | None = ...,
        api_key: str | None = ...,
    ) -> None: ...
    def configure(self) -> None: ...

class Provision(Component):
    project: str | None
    api_key: str | None
    location: str
    vm_environment_class: str
    vm_environment: str | None
    env_name: str | None
    diff: dict[str, Any] | None
    dry_run: bool | None

    def __init__(
        self,
        *,
        project: str | None = ...,
        api_key: str | None = ...,
        location: str = ...,
        vm_environment_class: str = ...,
        vm_environment: str | None = ...,
        env_name: str | None = ...,
        diff: dict[str, Any] | None = ...,
        dry_run: bool | None = ...,
    ) -> None: ...
    def load_env(self) -> Environment: ...
    def get_api(self) -> ServerProxy: ...
    def get_currently_provisioned_vms(self) -> list[dict[str, Any]]: ...
    def apply(self) -> None: ...
    def get_diff(self, old: list[dict[str, Any]], new: list[dict[str, Any]]) -> dict[str, dict[str, Any]]: ...

class DirectoryXMLRPC(Component):
    rg_name = Attribute(str)

    def __init__(
        self,
        *,
        rg_name: str | None = ...,
    ) -> None: ...
    def configure(self) -> None: ...

class MaintenanceStart(Component):
    def configure(self) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...

class MaintenanceEnd(Component):
    def configure(self) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...
