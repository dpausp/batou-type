---
lifecycle:
  requirements:
    completed_at: "2026-04-29T14:00:00Z"
    git_rev: "eaf9b21"
  design:
    completed_at: "2026-04-29T15:00:00Z"
    git_rev: "401577d"
  implement:
    completed_at: "2026-05-03T12:00:00Z"
    git_rev: "7e246be"
---

# stogger-convention-fixes

## Context

batou-type has 14 stogger convention violations in 2 files (`__init__.py`: 1, `cli.py`: 13) plus 9 uncovered event IDs in the logging-coverage check. The violations block a green test run. Simultaneously, user-facing output is redesigned: clear separation between user output (`log.info` with `_replace_msg`) and internals (`log.debug`), plus new summary events.

## Decisions

### function-visibility

#### Context

`_run_check` is a private function (`_` prefix) containing 9 `log.info()` calls. Stogger requires `log.debug()` for private functions. The function contains genuine user-facing events (projects found, checking components, results). Making it public allows `log.info()` with `_replace_msg`.

#### Decision

Rename `_run_check` to `run_check` (remove underscore). Single caller is `check()` at line 290 — trivial rename.

#### Alternatives

a. All `log.info` → `log.debug` — user sees nothing in normal operation
b. Keep private, public caller emits info-events — logging logic moves up, more code

#### Consequences

Mixed logging in public function: `log.info` for user output, `log.debug` for internals. All `log.info` calls require `_replace_msg`.

### branch-dedup

#### Context

`run_check` (formerly `_run_check`, lines 94-234) has two duplicated branches: JSON mode (L151-183) and human mode (L187-234). Both perform identical venv detection and checking-components logging. Six of the 9 violations appear in both branches with identical event IDs.

#### Decision

Extract a single loop over projects with shared venv detection + logging + `check_all()` call. Only result processing branches: JSON output to stdout vs. console printing. Eliminates duplication and half the violations.

#### Alternatives

a. Keep both branches, fix each independently — less risk but 6 violations fixed twice
b. Extract only logging into helper, keep branch structure — partial dedup

#### Consequences

Single source of truth for project-iteration logging. New events only need to be added once. Slightly restructured function body.

### venv-logging-level

#### Context

`project-venv` and `no-venv` events are currently `log.info`. Venv type (appenv vs regular) is an implementation detail — the user sees results regardless.

#### Decision

Both events become `log.debug()`. No `_replace_msg` needed.

#### Alternatives

a. Keep `log.info` with `_replace_msg` — useful but noisy for most users
b. `log.warning` for `no-venv`, `log.debug` for `project-venv` — no-venv is not necessarily problematic

#### Consequences

Quieter default output. Venv details available via debug level.

### no-projects-found-level

#### Context

When no batou projects are found, the user must notice. Currently `log.info` without `_replace_msg` and without kwargs — violates both `log-context-required` and `log-requires-replace-msg`.

#### Decision

Change to `log.warning("no-projects-found", _replace_msg="No batou projects found in {paths}", paths=[str(p) for p in paths])`. Warning level is noticeable but not a hard exit.

#### Alternatives

a. `log.info` — neutral, might be overlooked
b. Exit with error code + `log.error` — too aggressive, can be intentional

#### Consequences

Solves three violations at once: `except-must-log` equivalent, `log-context-required` (kwargs present), `log-requires-replace-msg` (warning requires `_replace_msg`).

### component-result-events

#### Context

No per-component events exist. Requirements called for "Checking {component}..." progress, but `check_all()` runs once per project — per-component pre-check logging is impossible. Results are per-component though.

#### Decision

Emit per-component result events AFTER check in the result-processing loop: `log.info("component-result", _replace_msg="{component}: {status}", component=name, passed=not result.has_errors)`. This shows each component's outcome.

#### Alternatives

a. Per-component events before check via single `check_file()` calls — would require core.py changes, violates architecture
b. No per-component events — only project-level "Checking N component(s)" + summary

#### Consequences

Per-component visibility in logs. Fits the actual execution model (check once per project, results per component).

### summary-events

#### Context

No structured summary events exist. User needs a clear pass/fail overview per project and overall.

#### Decision

Add two summary events: `log.info("components-failed", _replace_msg="{count} component(s) failed: {names}", ...)` when errors exist, and `log.info("components-passed", _replace_msg="All {count} component(s) passed", ...)` when clean. Both modes (JSON and human) emit these on stderr.

#### Alternatives

a. Summary only in human mode — JSON mode has data in stdout
b. Only failure summary, skip pass summary — less noise

#### Consequences

Consistent diagnostic output regardless of mode. JSON mode users get quick summary on stderr alongside structured data on stdout.

### bind-strategy

#### Context

Key `project` appears 4+ times as keyword argument in `run_check`. Stogger requires `log.bind()` for keys repeating 3+ times.

#### Decision

`log = log.bind(project=str(project))` once per project iteration. Remove `project=` kwargs from individual calls.

#### Alternatives

a. Split function so `project` appears <3 times per function — refactoring overhead
b. `# stogger: ignore` — repetition is fine for readability

#### Consequences

Structured context set once, `project` key available in all subsequent events of that iteration.

### except-block-logging

#### Context

Two except blocks have no log calls: `__init__.py:24` (PackageNotFoundError during version detection) and `cli.py:59` (stub detection fallback). Both violate `except-must-log`.

#### Decision

Add `log.debug("version-fallback")` in `__init__.py` (requires adding structlog import + get_logger). Add `log.debug("stub-not-external", name=name)` in `_detect_stub` except block.

#### Alternatives

a. `# stogger: ignore` — documents intentional silence but less observability
b. Restructure to avoid try/except — larger refactoring

#### Consequences

Full observability over version detection and stub resolution. Debug level avoids noise.

### test-strategy

#### Context

Existing tests are E2E via subprocess, checking stderr strings directly. Stogger `log.has()` only works in-process. Need both: E2E coverage for CLI integration and in-process coverage for logging-coverage check.

#### Decision

Hybrid approach: existing E2E tests continue checking stderr for user-facing events. New in-process unit tests call `run_check()` directly with `log.has("event-id")` assertions for all event IDs (existing + new). Test file: `tests/test_logging.py`.

#### Alternatives

a. E2E only with stderr string checks — logging-coverage check stays red
b. In-process only — loses E2E CLI integration coverage

#### Consequences

Green stogger checks. E2E coverage preserved. New test file with focused logging assertions.

## Requirements

### Event Catalog

**log.info (user-visible, all require `_replace_msg`):**

| Event ID | _replace_msg template | Context keys |
|----------|----------------------|-------------|
| `projects-found` | `"Found {count} project(s)"` | count |
| `project` | `"  {path}"` | path |
| `checking-components` | `"Checking {count} component(s) in {project}"` | count (project via bind) |
| `component-result` | `"{component}: {status}"` | component, passed |
| `components-failed` | `"{count} component(s) failed: {names}"` | count, names |
| `components-passed` | `"All {count} component(s) passed"` | count |

**log.warning:**

| Event ID | _replace_msg template | Context keys |
|----------|----------------------|-------------|
| `no-projects-found` | `"No batou projects found in {paths}"` | paths |

**log.debug (internals):**

| Event ID | Context keys |
|----------|-------------|
| `version-fallback` | — |
| `stub-not-external` | name |
| `stub-info` | name, version, path |
| `stub-not-installed` | name |
| `python-info` | executable |
| `project-venv` | kind, path |
| `no-venv` | — (project via bind) |

### Scope

- IN: `__init__.py`, `cli.py`, new `tests/test_logging.py`
- IN: All 14 convention violations fixed
- IN: New events: `component-result`, `components-failed`, `components-passed`
- IN: All event IDs covered by test assertions
- OUT: No other source files, no changes to stogger rules
- OUT: No changes to `core.py` or `output.py`

### Violation Resolution

| File | Rule | Resolution |
|------|------|-----------|
| `__init__.py:24` | except-must-log | `log.debug("version-fallback")` |
| `cli.py:59` | except-must-log | `log.debug("stub-not-external", name=name)` |
| `cli.py:94` | private-no-log-info | Rename `_run_check` → `run_check` |
| `cli.py:×9` | log-requires-replace-msg | `_replace_msg` on all `log.info()` calls |
| `cli.py:94` | log-use-bind-for-repeating-keys | `log.bind(project=...)` per iteration |
| `cli.py:128` | log-context-required | `log.warning` with kwargs |
| Tests | logging-coverage | `log.has()` in `tests/test_logging.py` |

## Appendix

```yaml
implementation_plan:
  id: stogger-convention-fixes
  description: "Fix 14 stogger convention violations in __init__.py and cli.py: rename _run_check to run_check, deduplicate JSON/human branches, adjust logging levels, add new events (component-result, components-passed, components-failed), use log.bind for project context, add except-block logging, create tests/test_logging.py."
  git_rev: "7e246be"
  created_at: "2026-05-03T12:00:00Z"
  specs:
    - .agents/impl_specs/stogger-convention-fixes.md
  target_tests:
    - file: tests/impl_spec/test_stogger-convention-fixes.py
      tests:
        - test_run_check_is_public
        - test_run_check_is_callable
        - test_no_private_run_check_exists
        - test_single_project_loop
        - test_venv_detection_in_single_location
        - test_check_all_called_once_in_loop
        - test_venv_events_at_debug_level
        - test_project_venv_has_kind_and_path
        - test_no_venv_no_replace_msg
        - test_emits_no_projects_found
        - test_no_projects_found_is_warning
        - test_no_projects_found_has_replace_msg
        - test_no_projects_found_has_paths_context
        - test_emits_component_result
        - test_component_result_is_info_level
        - test_component_result_has_replace_msg
        - test_component_result_has_component_and_passed
        - test_component_result_has_status
        - test_emits_components_passed
        - test_components_passed_is_info_level
        - test_components_passed_has_replace_msg
        - test_components_passed_has_count
        - test_components_failed_has_replace_msg
        - test_components_failed_has_count_and_names
        - test_bind_in_source
        - test_project_context_in_checking_components
        - test_project_context_in_component_result
        - test_no_explicit_project_kwarg_on_checking_components
        - test_init_has_version_fallback_log
        - test_init_has_structlog_import
        - test_cli_has_stub_not_external_log
        - test_stub_not_external_has_name_context
        - test_logging_test_file_exists
        - test_logging_file_has_event_assertions
        - test_logging_file_uses_capture_logs
        - test_logging_file_tests_event_levels
```
