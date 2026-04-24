from batou.component import Component
from batou_ext import nix
from batou_ext.fcio import Provision  # noqa


class Common(Component):
    def configure(self):
        self += nix.Package(attribute="nixos.nixfmt")
