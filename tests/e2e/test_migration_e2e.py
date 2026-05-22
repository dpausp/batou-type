"""E2E smoke tests for migration testing workflow.

Simulates what happens when newer stubs reveal breaking API changes
in existing deployment component code — the core value proposition of
batou-type migration testing.

Architecture rule: this file is E2E — it may only invoke the CLI as a
subprocess. Do NOT import from batou_type directly.
"""


def test_removed_attribute_reports_error(tmp_path, run_cli) -> None:
    """Stubs don't define an attribute the component uses — error reported.

    Simulates a migration scenario where batou removed an attribute that
    existing component code still references.
    """
    components = tmp_path / "components"
    components.mkdir()
    (components / "mycomponent.py").write_text(
        "from batou.component import Component\n"
        "\n"
        "\n"
        "class MyComp(Component):\n"
        "    def configure(self):\n"
        "        self.legacy_method_that_was_removed()\n"
    )

    result = run_cli("check", cwd=tmp_path)
    assert result.returncode == 1
    combined = result.stdout + result.stderr
    assert "error" in combined.lower()


def test_signature_shift_reports_error(tmp_path, run_cli) -> None:
    """Stubs changed a method signature — mismatch caught.

    Simulates a migration scenario where a method's parameter types
    changed between batou versions.
    """
    components = tmp_path / "components"
    components.mkdir()
    (components / "mycomponent.py").write_text(
        "from batou.component import Component\n"
        "\n"
        "\n"
        "class MyComp(Component):\n"
        "    def configure(self):\n"
        "        # cmd() expects str as first arg, not int\n"
        "        self.cmd(123)\n"
    )

    result = run_cli("check", cwd=tmp_path)
    assert result.returncode == 1
    combined = result.stdout + result.stderr
    assert "error" in combined.lower()


def test_clean_component_exits_zero(tmp_path, run_cli) -> None:
    """Component matching current stubs — exit 0.

    Confirms that component code conforming to the current stubs
    passes cleanly (baseline for migration testing).
    """
    components = tmp_path / "components"
    components.mkdir()
    (components / "mycomponent.py").write_text(
        "from batou.component import Component\n"
        "\n"
        "\n"
        "class MyComp(Component):\n"
        "    def configure(self) -> None:\n"
        "        self.cmd('echo hello')\n"
    )

    result = run_cli("check", cwd=tmp_path)
    assert result.returncode == 0
