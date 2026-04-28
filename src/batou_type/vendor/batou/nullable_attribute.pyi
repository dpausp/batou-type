from collections.abc import Callable
from typing import Any, Self, overload

from batou.component import Attribute

class NullableAttribute[T](Attribute[T]):
    """Attribute that defaults to None — __get__ returns T | None."""

    # Type conversion — T from conversion
    @overload
    def __init__(
        self,
        conversion: type[T],
        *,
        expand: bool = ...,
        map: bool = ...,
    ) -> None: ...

    # Callable conversion — T from callable
    @overload
    def __init__(
        self,
        conversion: Callable[..., T],
        *,
        expand: bool = ...,
        map: bool = ...,
    ) -> None: ...
    @overload
    def __get__(self, obj: None, objtype: type | None = ...) -> Self: ...
    @overload
    def __get__(self, obj: Any, objtype: type | None = ...) -> T | None: ...
