from pathlib import Path

from batou.component import Component
from batou.lib.file import Purge

class NixOSModuleContext(Component):
    source_component: Component | None
    prefix: str | None

    def __init__(
        self,
        *,
        source_component: Component | None = ...,
        prefix: str | None = ...,
    ) -> None: ...

class NixOSModule(Component):
    namevar: str
    name: str | None
    path: Path
    context: Component | None

    def __init__(
        self,
        name: str | None = ...,
        *,
        path: Path = ...,
        context: Component | None = ...,
    ) -> None: ...
    def configure(self) -> None: ...

class PurgeNixOSModule(Purge):
    namevar: str
    name: str
    path: Path

    def configure(self) -> None: ...
