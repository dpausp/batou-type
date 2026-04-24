from typing import Any

from batou.component import Attribute, Component

class S3(Component):
    endpoint_url = Attribute(str)
    access_key_id = Attribute(str)
    secret_access_key = Attribute(str)
    client: Any  # boto3 S3 resource

    def __init__(
        self,
        *,
        endpoint_url: str = ...,
        access_key_id: str = ...,
        secret_access_key: str = ...,
    ) -> None: ...
    def configure(self) -> None: ...

class Bucket(Component):
    namevar: str
    bucketname: str | None
    s3: S3

    def __init__(
        self,
        bucketname: str | None = ...,
        *,
        s3: S3 | None = ...,
    ) -> None: ...
    def configure(self) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...

class Download(Component):
    namevar: str
    s3 = Attribute(str)
    key = Attribute(str)
    bucketname = Attribute(str)
    target = Attribute(str)
    checksum: str | None  # type: ignore[assignment]

    def __init__(
        self,
        key: str | None = ...,
        *,
        s3: str = ...,
        bucketname: str = ...,
        target: str = ...,
        checksum: str | None = ...,
    ) -> None: ...
    def configure(self) -> None: ...
    def verify(self) -> None: ...
    def update(self) -> None: ...
