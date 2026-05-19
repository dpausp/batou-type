# batou-type

Type-check batou deployment components against bundled stubs — catches attribute errors and missing imports before deploying.

## The problem

batou components are Python, but errors like misspelled attributes or missing imports from `batou_ext` only surface at deploy time. batou-type catches these statically by shipping bundled type stubs for the [batou](https://github.com/flyingcircusio/batou) and [batou_ext](https://github.com/flyingcircusio/batou_ext) APIs.

## Quick start

```{code-block} shell
$ pip install batou-type
$ batou-type check
```

Expected output when all components pass:

```{code-block} text
2026-05-19T20:03:12Z I projects-found                 Found 1 project(s)
2026-05-19T20:03:12Z I checking-components            Checking 1 component(s) in /deploy/my-deployment
2026-05-19T20:03:13Z I component-passed               myapp passed type check (ty)
2026-05-19T20:03:13Z I components-passed              All 1 component(s) passed
```

Output uses structured logging with ISO timestamps. In a terminal, errors appear in red.

```{toctree}
:maxdepth: 2
:caption: User Guide

user/index
```

```{toctree}
:maxdepth: 2
:caption: Developer Guide

dev/index
```

```{toctree}
:maxdepth: 2
:caption: API Reference

autoapi/index
```
