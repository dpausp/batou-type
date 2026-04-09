"""Type-check batou deployments against batou stubs."""

import subprocess
import sys
from pathlib import Path


def main() -> None:
    cwd = Path.cwd()
    components = sorted(cwd.glob("components/**/*.py"))

    if not components:
        print("No component files found in components/", file=sys.stderr)
        sys.exit(0)

    print(
        f"Type-checking {len(components)} component file(s) ...",
        file=sys.stderr,
    )

    paths = [str(p) for p in components]
    result = subprocess.run(["ty", "check", *paths])

    sys.exit(result.returncode)
