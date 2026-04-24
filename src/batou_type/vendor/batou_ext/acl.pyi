from batou.component import Attribute, Component

class ACL(Component):
    namevar: str
    path: str
    ruleset = Attribute(list)

    def __init__(
        self,
        path: str = ...,
        *,
        ruleset: list[str] = ...,
    ) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...
