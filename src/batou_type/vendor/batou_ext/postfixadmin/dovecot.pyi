from batou.component import Component

class PFADovecot(Component):
    local_conf: str
    database_conf: str

    def __init__(
        self,
        *,
        local_conf: str = ...,
        database_conf: str = ...,
    ) -> None: ...
    def configure(self) -> None: ...
