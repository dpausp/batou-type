from batou.component import Attribute, Component
from batou.lib.file import File

class PodmanRuntime(Component): ...

class Container(Component):
    image = Attribute(str)
    container_name = Attribute(str)
    health_cmd = Attribute(str, None)
    user = Attribute(str, None)
    pull_always: bool
    registry_address = Attribute(str, None)
    registry_user = Attribute(str, None)
    registry_password = Attribute(str, None)
    version: str
    monitor: bool
    rebuild: bool
    entrypoint: str | None
    docker_cmd: str | None
    envfile: File | None
    mounts: dict[str, str]
    ports: dict[str, str]
    env: dict[str, str]
    depends_on: list[str] | None
    extra_options: list[str]
    oneshot: bool

    def __init__(
        self,
        *,
        image: str = ...,
        container_name: str = ...,
        health_cmd: str | None = ...,
        user: str | None = ...,
        pull_always: bool = ...,
        registry_address: str | None = ...,
        registry_user: str | None = ...,
        registry_password: str | None = ...,
        version: str = ...,
        monitor: bool = ...,
        rebuild: bool = ...,
        entrypoint: str | None = ...,
        docker_cmd: str | None = ...,
        envfile: File | None = ...,
        mounts: dict[str, str] = ...,
        ports: dict[str, str] = ...,
        env: dict[str, str] = ...,
        depends_on: list[str] | None = ...,
        extra_options: list[str] = ...,
        oneshot: bool = ...,
    ) -> None: ...
    def activate(self) -> ContainerRestart: ...

class ContainerRestart(Component):
    namevar: str
    container: Container

    def __init__(
        self,
        container: str | None = ...,
    ) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...
