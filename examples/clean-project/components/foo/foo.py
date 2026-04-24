from batou.component import Attribute, Component
from batou.lib.file import Directory, File, Purge
from batou.utils import Address


class Foo(Component):
    # Secrets
    admin_password = Attribute(str, default=None)

    # Settings
    create_admin = Attribute(bool, default=False)
    fqdn = Attribute(str)
    port = Attribute(int, default=8080)

    def configure(self):
        if self.create_admin:
            self += File(
                "admin_password",
                mode=0o0640,
                content=self.admin_password,
                sensitive_data=True,
            )
        else:
            self += Purge("admin_password")

        self.address: Address = Address(self.fqdn, self.port)

        self.base_url: str = f"https://{self.fqdn}"

        self += Directory("directory")
        self += File("directory/template.txt")
