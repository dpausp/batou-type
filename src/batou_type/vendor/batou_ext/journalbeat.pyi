from batou.component import Attribute, Component

class JournalBeatTransport(Component):
    nix_file_path = Attribute(str)
    transport_name = Attribute(str)
    graylog_host = Attribute(str)
    graylog_port = Attribute(int)

    def __init__(
        self,
        *,
        nix_file_path: str = ...,
        transport_name: str = ...,
        graylog_host: str = ...,
        graylog_port: int = ...,
    ) -> None: ...
    def configure(self) -> None: ...
