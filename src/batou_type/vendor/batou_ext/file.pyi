from batou.component import Attribute, Component

class SymlinkAndCleanup(Component):
    namevar: str
    pattern: str | None
    etag_suffix = Attribute(str)
    prefix: str | None
    systemd_read_max_iops: int
    systemd_write_max_iops: int
    trashdir: str | None
    trash_config_file_name = Attribute(str)
    use_systemd_run_async_cleanup: bool
    systemd_extra_args: str | None

    def __init__(
        self,
        current: str | None = ...,
        *,
        etag_suffix: str = ...,
        trash_config_file_name: str = ...,
        pattern: str | None = ...,
        prefix: str | None = ...,
        systemd_read_max_iops: int = ...,
        systemd_write_max_iops: int = ...,
        trashdir: str | None = ...,
        use_systemd_run_async_cleanup: bool = ...,
        systemd_extra_args: str | None = ...,
    ) -> None: ...
    def configure(self) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...

class DeploymentTrash(Component):
    file_name = Attribute(str)
    read_iops_limit: int
    write_iops_limit: int
    trashdir: str | None

    def __init__(
        self,
        *,
        file_name: str = ...,
        read_iops_limit: int = ...,
        write_iops_limit: int = ...,
        trashdir: str | None = ...,
    ) -> None: ...
    def configure(self) -> None: ...
    def discard(self, path: str) -> None: ...
