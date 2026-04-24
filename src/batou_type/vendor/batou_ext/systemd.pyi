from batou.component import Attribute, Component

class ScalableService(Component):
    namevar: str
    running_instances = Attribute(int)

    def __init__(
        self,
        base_name: str | None = ...,
        *,
        running_instances: int = ...,
    ) -> None: ...
    def configure(self) -> None: ...
