from batou.component import Attribute, Component

from batou_ext.file import SymlinkAndCleanup

class GitCheckout(Component):
    git_host: str | None
    git_clone_url: str | None
    git_revision: str | None
    git_target: str | None
    git_port: str | None
    exclude: tuple[str, ...]
    sync_parent_folder: str | None
    scan_host: bool

    def __init__(
        self,
        *,
        git_host: str | None = ...,
        git_clone_url: str | None = ...,
        git_revision: str | None = ...,
        git_target: str | None = ...,
        git_port: str | None = ...,
        exclude: tuple[str, ...] = ...,
        sync_parent_folder: str | None = ...,
        scan_host: bool = ...,
    ) -> None: ...
    def configure(self) -> None: ...
    def symlink_and_cleanup(self) -> SymlinkAndCleanup: ...

class Commit(Component):
    namevar: str
    message: str | None
    workingdir: str
    author_name: str
    author_email: str

    def __init__(
        self,
        filename: str | None = ...,
        *,
        message: str | None = ...,
        workingdir: str = ...,
        author_name: str = ...,
        author_email: str = ...,
    ) -> None: ...
    def configure(self) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...
    def has_changes(self) -> bool: ...

class Remote(Component):
    namevar: str
    url = Attribute(str)
    name = Attribute(str)
    ignore_not_existing = Attribute(bool)

    def __init__(
        self,
        git_repo: str | None = ...,
        *,
        url: str = ...,
        name: str = ...,
        ignore_not_existing: bool = ...,
    ) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...

class Push(Component):
    workingdir: str

    def __init__(
        self,
        *,
        workingdir: str = ...,
    ) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...
    def has_outgoing_changesets(self) -> bool: ...

class StopDeployOnLocalGitChange(Component):
    namevar: str
    target: str | None

    def __init__(
        self,
        target: str | None = ...,
    ) -> None: ...
    def verify(self) -> None: ...
