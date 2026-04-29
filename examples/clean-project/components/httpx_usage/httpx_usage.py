"""Harmless httpx usage - should pass type check."""

import httpx
from batou.component import Attribute, Component
from batou.lib.file import File


class HttpxUsage(Component):
    api_url = Attribute(str, default="https://api.example.com")

    def configure(self):
        httpx.Client(
            base_url=self.api_url,
            timeout=30.0,
        )
        # Just store the URL config - harmless
        self += File("api_config.txt", content=self.api_url)
