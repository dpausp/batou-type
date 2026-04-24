from batou.component import Component

from batou_ext.cron import CronJob, SystemdTimer
from batou_ext.file import SymlinkAndCleanup
from batou_ext.mail import Mailpit
from batou_ext.postgres import DB, User as PGUser
from batou_ext.redis import Redis
from batou_ext.run import Run


class ExtTest(Component):
    def configure(self) -> None:
        # No-namevar component (keyword-only args)
        self += Redis(db=0, port=6379)

        # Namevar components
        self += CronJob("myjob", command="echo hello", timing="@daily")
        self += SystemdTimer(
            "timer1", command="echo hi", onCalendar="*-*-* 00:00:00"
        )
        self += DB("mydb", owner="postgres")
        self += PGUser("myuser", password="secret")
        self += Run("echo test")
        self += SymlinkAndCleanup("/srv/app/current")

        # Component with Attribute-based config
        self += Mailpit(public_name="mail.example.com")
