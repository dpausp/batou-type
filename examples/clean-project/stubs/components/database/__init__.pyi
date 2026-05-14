from batou.component import Component


class Database(Component):
    host: str
    port: int
    dbname: str
