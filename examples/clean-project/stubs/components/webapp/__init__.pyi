from typing import overload
from batou.component import Component
from components.database.database import Database


class Webapp(Component):
    @overload
    def require_one(self, key: "database") -> Database: ...
    @overload
    def require_one(self, key: str) -> object: ...
