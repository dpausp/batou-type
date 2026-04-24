# testproject.batou

Test-Deployment zum Entwickeln und Validieren von `batou-typecheck` samt der
Stub-Pakete `batou-stubs` und `batou_ext-stubs`.

## Setup

```bash
uv sync
```

Installiert batou, die Stub-Pakete und `batou-typecheck` (alles als
non-editable-Installs, damit die `.pyi`-Dateien in `site-packages` landen).

**Wichtig**: Nach Änderungen an den Stub-Paketen oder batou-typecheck muss
neu installiert werden — `uv sync` allein reicht nicht:

```bash
uv pip install --force-reinstall --no-deps ../batou/batou-stubs
uv pip install --force-reinstall --no-deps ../batou-typecheck
uv pip install --force-reinstall --no-deps ../batou_ext/batou_ext-stubs
```

## batou-typecheck nutzen

```bash
uv run batou-typecheck
```

Prüft alle `components/**/*.py`-Dateien nacheinander mit drei Type-Checkern:
**ty**, **mypy**, **basedpyright**. Pro Datei wird ein separater Subprocess
gestartet.

### Einzelne Checker

```bash
uv run batou-typecheck --checker ty
uv run batou-typecheck --checker mypy
uv run batou-typecheck --checker basedpyright
```

### Alle Checker (default)

```bash
uv run batou-typecheck --checker ty --checker mypy --checker basedpyright
```

### Specific mypy flags

`batou-typecheck` setzt `--check-untyped-defs` für mypy — ohne das würde
mypy Funktionskörper ohne Return-Type-Annotation überspringen und die meisten
batou-Fehler verpassen.

basedpyright-Noise (`reportImplicitOverride`, `reportUnannotatedClassAttribute`,
`reportUninitializedInstanceVariable`) wird automatisch gefiltert.

## Test-Komponenten

| Komponente | Typ | Beschreibung |
|---|---|---|
| `bad_address` | Bug | `Address(42, 8080)` — int statt str für connect_address |
| `bad_content` | Bug | `File("config.txt", content=12345)` — int statt str |
| `bad_default` | Bug | `Attribute(str, default=42)` — Default-Typ passt nicht zur Konversion |
| `multi_error` | Bug | Drei Fehler: Address mit list, File mit list, nonexistent method |
| `silent_bugs` | False Negatives | Bugs die Checker wahrscheinlich nicht finden (bool<:int, str→bool) |
| `foo` | Clean | Korrekte Komponente mit Attributes, File, Directory, Address |
| `common` | Clean | Nutzt batou_ext (nix.Package, fcio.Provision) |
| `ext_test` | Clean | Batou_ext-Komponenten: Redis, CronJob, SystemdTimer, DB, Mailpit etc. |

### Erwartete Ergebnisse

```
ty:           ~5 errors   (Address-content, File-content, Attribute-default, multi_error)
mypy:         ~7 errors   (wie ty + stricter checks)
basedpyright: ~7 errors   (wie mypy + reportArgumentType)
```

Die `silent_bugs`-Komponente enthält absichtlich Fehler, die von allen drei
Checkern nicht erkannt werden — das dokumentiert die Grenzen des Ansatzes:
`bool <: int` ist im Typsystem korrekt, und String-Literal-Checks bei
sensitive_data greifen nicht.

## Architektur

```
testproject/
├── pyproject.toml          # batou + stubs + typecheck als deps
├── components/
│   ├── bad_address/        # Testfall: falscher Param-Typ
│   ├── bad_content/        # Testfall: falscher content-Typ
│   ├── bad_default/        # Testfall: Attribute default mismatch
│   ├── multi_error/        # Testfall: mehrere Fehler gleichzeitig
│   ├── silent_bugs/        # Testfall: false negatives
│   ├── foo/                # Clean: vollständige Komponente
│   ├── common/             # Clean: batou_ext-Integration
│   └── ext_test/           # Clean: batou_ext-Komponenten
└── environments/           # batou-Umgebungen
```

## Abhängigkeiten

| Paket | Quelle | Zweck |
|---|---|---|
| `batou` | PyPI | Deployment-Framework |
| `batou-stubs` | `../batou/batou-stubs` | PEP 561 Stubs für batou core |
| `batou_ext-stubs` | `../batou_ext/batou_ext-stubs` | PEP 561 Stubs für batou_ext |
| `batou-typecheck` | `../batou-typecheck` | CLI-Tool zum Prüfen der Komponenten |
