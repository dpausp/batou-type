from batou.component import Component

def dict_merge(a: dict[str, str], b: dict[str, str]) -> dict[str, str]: ...

class RegexPatch(Component):
    namevar: str
    source: str | None
    pattern: str | None
    replacement: str | None

    def __init__(
        self,
        path: str | None = ...,
        *,
        source: str | None = ...,
        pattern: str | None = ...,
        replacement: str | None = ...,
    ) -> None: ...
    def configure(self) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...

class MultiRegexPatch(Component):
    namevar: str
    patterns: tuple[str, ...]

    def __init__(
        self,
        path: str | None = ...,
        *,
        patterns: tuple[str, ...] = ...,
    ) -> None: ...
    def configure(self) -> None: ...
