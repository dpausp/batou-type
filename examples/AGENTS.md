# examples

**Generated:** 2026-05-05

Sample batou deployments used by the test suite and for manual verification.

## Structure

    clean-project/    No type errors — all component attributes match stubs
    error-project/    Contains deliberate type errors for E2E failure testing
    mixed-project/    Has `.venv/` present — tests venv detection logic

Each project has `components/` with `.py` files, `pyproject.toml` with batou deps, and follows standard batou deployment layout.
