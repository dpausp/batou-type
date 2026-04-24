"""BUG: Type error using boto + batou - content expects str, gets S3Connection."""

from boto.s3.connection import S3Connection
from batou.component import Attribute, Component
from batou.lib.file import File


class BotoBadUsage(Component):
    bucket_name = Attribute(str, default="my-bucket")

    def configure(self):
        conn: S3Connection = S3Connection()
        # BUG: File content expects str, but we pass an S3Connection object
        self += File("s3_config.txt", content=conn)
