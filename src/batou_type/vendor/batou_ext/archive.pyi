from batou.component import Attribute
from batou.lib.archive import Untar

class SingleUntar(Untar):
    cleanup_markers_after_days = Attribute(int)

    def __init__(
        self,
        archive: str | None = ...,
        *,
        target: str = ...,
        create_target_dir: bool = ...,
        strip: int = ...,
        cleanup_markers_after_days: int | None = ...,
    ) -> None: ...
    def configure(self) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...
