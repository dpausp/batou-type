# pytest Integration

Add type checking to your pytest test suite with `--batou-ty`:

```{code-block} shell
$ pytest --batou-ty
```

The plugin registers automatically via the `pytest11` entry point — no extra configuration needed.

The plugin collects all `components/**/*.py` files as test items, runs ty on each component before the test session, and reports type errors as test failures.

Each component file appears as a single test item marked with the `batou_ty` marker.

A passing type check produces:

```{code-block} text
PASSED components/app/component.py::batou_ty
```

A failing type check produces:

```{code-block} text
FAILED components/app/component.py::batou_ty - Type check failed with 3 error(s)
```

## Filter tests

```{code-block} shell
$ pytest --batou-ty -m batou_ty       # run only type-check tests
$ pytest --batou-ty -k "app"          # type-check only matching components
```
