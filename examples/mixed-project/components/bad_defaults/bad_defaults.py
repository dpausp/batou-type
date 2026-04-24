"""BUG: Multiple Attribute default values that don't match their conversion type."""

from batou.component import Attribute, Component


class BadDefaults(Component):
    # BUG: int default for str conversion
    name = Attribute(str, default=42)

    # BUG: str default for int conversion — will crash at configure time
    # when batou tries int("8080") which works, but the type is still wrong
    port = Attribute(int, default="8080")

    # BUG: dict default for list conversion — completely wrong container type
    tags = Attribute(list, default={"key": "value"})

    # BUG: None default for int — non-Optional int gets None
    timeout = Attribute(int, default=None)

    # BUG: str default for bool conversion — "truthy" string instead of bool
    enabled = Attribute(bool, default="yes")

    # BUG: int default for list conversion — scalar where collection expected
    hosts = Attribute(list, default=1)
