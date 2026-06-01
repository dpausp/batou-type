class XSpec:
    chdir: str | None
    dont_write_bytecode: bool | None
    execmodel: str | None
    id: str | None
    installvia: str | None
    nice: str | None
    popen: bool | None
    python: str | None
    socket: str | None
    ssh: str | None
    ssh_config: str | None
    vagrant_ssh: str | None
    via: str | None
    env: dict[str, str | bool]

    def __init__(self, string: str) -> None: ...
    def __repr__(self) -> str: ...
    def __str__(self) -> str: ...
    def __hash__(self) -> int: ...
    def __eq__(self, other: object) -> bool: ...
    def __ne__(self, other: object) -> bool: ...
