from batou.component import Attribute, Component, ConfigString

class CronJob(Component):
    namevar: str
    command: str | None
    timing: str | None
    log_file: str | None
    lock_file: str | None
    stamp_file: str | None
    timeout: str
    checkWarning: int | None
    checkCritical: int | None
    args: str

    def __init__(
        self,
        tag: str | None = ...,
        *,
        command: str | None = ...,
        timing: str | None = ...,
        log_file: str | None = ...,
        lock_file: str | None = ...,
        stamp_file: str | None = ...,
        timeout: str = ...,
        checkWarning: int | None = ...,
        checkCritical: int | None = ...,
        args: str = ...,
    ) -> None: ...
    def format(self) -> str: ...
    def configure(self) -> None: ...

class SystemdTimer(Component):
    namevar: str
    command = Attribute(str)
    onCalendar = Attribute(str)
    persistent: bool
    timeout: str
    description: str | None
    additional_service_config: str | None
    run_as = Attribute(str)

    def __init__(
        self,
        tag: str | None = ...,
        *,
        command: str = ...,
        onCalendar: str = ...,
        persistent: bool = ...,
        run_as: str | ConfigString = ...,
        timeout: str = ...,
        description: str | None = ...,
        additional_service_config: str | None = ...,
    ) -> None: ...
    def configure(self) -> None: ...
