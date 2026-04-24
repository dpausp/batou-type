"""BUG: File content expects str, gets int."""

from batou.component import Component
from batou.lib.file import File


class BadContent(Component):
    def configure(self):
        # BUG: content should be str, not int
        self += File("config.txt", content=12345)
