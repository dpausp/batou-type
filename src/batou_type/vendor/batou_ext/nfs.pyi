from batou.component import Attribute, Component, ConfigString

class NFS(Component):
    basepath = Attribute(str)
    serverpath = Attribute(str)

    def __init__(
        self,
        *,
        basepath: str | ConfigString = ...,
        serverpath: str | ConfigString = ...,
    ) -> None: ...
    def configure(self) -> None: ...
