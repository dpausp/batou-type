"""Harmless boto usage - should pass type check."""

from boto.s3.connection import S3Connection
from batou.component import Attribute, Component
from batou.lib.file import File


class BotoUsage(Component):
    bucket_name = Attribute(str, default="my-bucket")

    def configure(self):
        # Harmless: just building an S3 connection string
        # boto is untyped, so this should pass without errors
        conn: S3Connection = S3Connection()
        self.endpoint: str = f"s3://{self.bucket_name}"
        self += File("s3_config.txt", content=self.endpoint)
