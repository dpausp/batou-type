from batou.component import Attribute, Component


class Webapp(Component):
    appname = Attribute(str, default="webapp")

    def configure(self):
        db = self.require_one("database")
        reveal_type(db)
        print(db.host)
        print(db.port)
        print(db.dbname)
        # This should error — no .password on Database
        print(db.password)
        # This should also error — no .totally_bogus on Database
        print(db.totally_bogus)
