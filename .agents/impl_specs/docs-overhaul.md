# docs-overhaul

## Context
Docs were written before docs-writing skill was established. Current docs violate Diataxis principles (mixing reference, how-to, tutorial, explanation in single pages), use passive voice and nominalizations, and miss key patterns (README "when not to use", effect-over-parameter descriptions in CLI help).

## Decisions

### diataxis-split

#### Context
usage.md (326 lines) mixes reference (flags, exit codes, JSON format), how-to (autofix, pytest, migration testing), and explanation (project discovery, venv detection) in one page.

#### Decision
Split into one page per Diataxis type:
- `user/reference.md` (new) — pure reference: all flags, exit codes, JSON format, checker options, venv detection, verbose output, version command
- `user/autofix.md` (new) — how-to: autofix flags, virtual mode, diff output
- `user/pytest.md` (new) — how-to: pytest integration with --batou-ty
- `user/migration.md` (new) — how-to: migration testing workflow
- `user/usage.md` — delete (content distributed to new pages)

#### Alternatives
a. Keep single usage.md — too long, mixes types, hard to navigate
b. Split by topic only (not by Diataxis type) — doesn't solve the fundamental problem

#### Consequences
More files but each page has clear purpose. Users find what they need faster.

### quickstart-cleanup

#### Context
quickstart.md includes "Common Issues" section that is troubleshooting, not tutorial material. Tutorial should be linear, no dead ends.

#### Decision
Remove "Common Issues" section from quickstart. Move troubleshooting content to relevant how-to pages or reference page if needed.

#### Consequences
Cleaner tutorial flow. Troubleshooting lives where it belongs.

### readme-template

#### Context
README missing "When not to use this" section and has some padding ("What It Checks" duplicates usage docs).

#### Decision
Apply README template: one-sentence opener, install, quick start, "when not to use", link to full docs. Remove "What It Checks" (duplicates docs) and "Autofix" (link instead).

#### Consequences
30-second decision for new users. Trust-building through honest limitations.

### cli-effect-descriptions

#### Context
CLI help strings describe parameters, not effects. Example: "Type checker(s) to run (default: ty)" says WHAT the parameter is, not WHAT IT DOES.

#### Decision
Rewrite all help strings to describe effects. Follow voice rules: effect not parameter, no passive, no nominalizations, friendly senior colleague tone.

#### Consequences
--help text that helps users understand behavior, not just parameters.

### dev-docs-voice

#### Context
Dev docs (architecture.md, testing.md) have some passive voice, long compound sentences, and nominalizations. Content is good but voice could be more direct.

#### Decision
Clean up voice: active verbs, shorter sentences, remove nominalizations. Keep technical precision. No content changes.

#### Consequences
Easier to read for contributors without losing technical depth.

## Voice Rules (apply to ALL files)
- Effect, not parameter: "Aborts after N seconds" not "Timeout in seconds"
- No nominalizations: "Configures X" not "Enables configuration of X"
- No passive without reason: use active verbs
- Mention failure cases when non-obvious
- Tone: friendly senior colleague, not manual author
- No LLM geschwurbel: no "It's important to note", no "In order to", no "enables", no "provides the ability to"

## File Changes Summary

### New files
- `docs/user/reference.md` — pure reference page
- `docs/user/autofix.md` — how-to for autofix
- `docs/user/pytest.md` — how-to for pytest integration
- `docs/user/migration.md` — how-to for migration testing

### Modified files
- `README.md` — apply template
- `docs/user/quickstart.md` — remove Common Issues
- `docs/user/index.md` — update toctree
- `docs/dev/architecture.md` — voice cleanup
- `docs/dev/testing.md` — voice cleanup
- `src/batou_type/cli.py` — fix help strings

### Deleted files
- `docs/user/usage.md` — content split to new pages
