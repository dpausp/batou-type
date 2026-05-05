# vendor

**Generated:** 2026-05-05

Bundled `.pyi` type stubs for `batou` and `batou_ext`. See ../../../docs/dev/architecture.md (Vendor Stubs System) for resolution logic.

## Structure

    batou/          24 stubs — core framework (component, agent, environment, host, repository, secrets/, lib/, migrate/)
    batou_ext/      36 stubs — extensions (nix, nixos, oci, postgres, redis, mysql, ssl, s3, etc.)

Both directories contain `py.typed` markers.

## Updating

Run `update-stubs.sh` from project root to sync from `../batou/stubs/` and `../batou_ext/stubs/` via rsync.
