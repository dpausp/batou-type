from typing import Any

from batou.component import Attribute, Component, ConfigString

class Pipenv(Component):
    target: str | None
    executable: str

    def __init__(
        self,
        *,
        target: str | None = ...,
    ) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...

class VirtualEnvRequirements(Component):
    version = Attribute(str)
    requirements_path = Attribute(str, ConfigString("requirements.txt"))
    pip_install_extra_args = Attribute(str)
    pre_run_script_path: str | None
    env: dict[str, str] | None
    venv: Any | None

    def __init__(
        self,
        *,
        version: str = ...,
        requirements_path: str | ConfigString = ...,
        pip_install_extra_args: str = ...,
        pre_run_script_path: str | None = ...,
        env: dict[str, str] | None = ...,
        venv: Any | None = ...,
    ) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...

class FixELFRunPath(Component):
    path = Attribute(str)
    env_directory = Attribute(str)
    glob_patterns: list[str]
    patchelf_jobs = Attribute(int)
    recurse_env_dir = Attribute(bool)

    def __init__(
        self,
        *,
        path: str = ...,
        env_directory: str = ...,
        glob_patterns: list[str] = ...,
        patchelf_jobs: int = ...,
        recurse_env_dir: bool = ...,
    ) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...

class BuildEnv(Component):
    version: str
    executable: str | None
    env_dir: str | None
    nix_file: str

    def __init__(
        self,
        *,
        version: str = ...,
        executable: str | None = ...,
        env_dir: str | None = ...,
        nix_file: str = ...,
    ) -> None: ...
    def configure(self) -> None: ...
    def environment_variables(self) -> dict[str, str]: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...
