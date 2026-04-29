"""BUG: Type error using httpx + batou - timeout expects float, gets str."""

import httpx
from batou.component import Attribute, Component
from batou.lib.file import File


class HttpxBadUsage(Component):
    api_url = Attribute(str, default="https://api.example.com")

    def configure(self):
        # BUG: timeout expects float/Timeout, not str
        httpx.Client(
            base_url=self.api_url,
            timeout="thirty seconds",
        )
        self += File("api_config.txt", content=self.api_url)
