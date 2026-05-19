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
Found 1 project(s)
Checking 3 component(s) in /deploy/my-deployment
app passed type check (ty)
database passed type check (ty)
webserver passed type check (ty)
All 3 component(s) passed
```

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
