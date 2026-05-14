from batou.component import Attribute, Component


class Database(Component):
    host = Attribute(str, default="localhost")
    port = Attribute(int, default=5432)
    dbname = Attribute(str, default="mydb")

    def configure(self):
        self.provide("database", self)
