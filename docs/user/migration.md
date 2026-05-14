# Migration Testing

Most valuable during **major version changes** — when batou introduces breaking API changes, renamed attributes, or removed parameters.

Preview breaking changes before upgrading batou in production.

1. Install a **newer** version of `batou-type` (which ships updated stubs) alongside your existing deployment.
2. Run `batou-type check`.
3. Type errors reveal API changes, removed attributes, or signature shifts that would break on upgrade.

Fix the reported issues in your components, then upgrade batou with confidence.

Example output:

```{code-block} text
components/app/component.py:42: error: unresolved-attribute  [ty]
  Attribute ``configure`` does not exist on ``Component``
  Component.configure was removed in batou 3.0 — use Component.update instead

Found 1 error in 1 file (checked 12 component files)
```
