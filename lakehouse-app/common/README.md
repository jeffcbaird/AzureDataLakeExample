# lakehouse-common

Shared Python library for the Azure Data Lakehouse. Provides ENV-aware path
resolution, HTTP/FTP base clients, Key Vault access, structured logging, and
the validation framework used by all Spark jobs.

## Installation

From the `lakehouse-feed` Azure Artifacts feed:

```bash
pip install lakehouse-common
```

With Spark extras (required by processing jobs):

```bash
pip install "lakehouse-common[spark]"
```

## Versioning policy

This package follows [Semantic Versioning 2.0.0](https://semver.org/):

| Change type | Version bump | Example |
|---|---|---|
| Backwards-compatible bug fix | Patch (`0.1.x`) | Fix a log format string |
| Backwards-compatible new feature | Minor (`0.x.0`) | Add a new client class |
| Breaking API change | Major (`x.0.0`) | Rename `get_secret()` → `fetch_secret()` |

**Every PR that touches `common/` must include a version bump in `pyproject.toml`.**
The CI `publish-common.yml` pipeline rejects releases if the version was not incremented.

### Consumer pinning requirements

All packages that depend on `lakehouse-common` must pin to a minimum version:

```
# requirements.txt / pyproject.toml
lakehouse-common>=0.1.0,<1.0.0   # ingestion, processing, validation
lakehouse-common[spark]>=0.1.0,<1.0.0  # processing jobs
```

The upper bound `<1.0.0` protects consumers from unintentional breaking changes
until the API is declared stable at `1.0.0`.

### Release process

1. Merge your PR into `main` with the version bump in `pyproject.toml`.
2. `publish-common.yml` automatically builds the wheel and publishes to `lakehouse-feed`.
3. Tag the commit: `git tag v<version> && git push --tags`.
4. Downstream consumers update their pin in a follow-up PR.

## Package structure

```
lakehouse_common/
├── clients/
│   ├── base_http.py      BaseHttpClient — requests wrapper with retry + structured logging
│   └── base_ftp.py       BaseFtpClient — paramiko SFTP + ftplib plain-FTP
├── config/
│   └── settings.py       Settings — ENV-aware path resolver (local ↔ abfss://)
├── keyvault/
│   └── client.py         get_secret() — cached SecretClient via DefaultAzureCredential
├── logging/
│   └── logger.py         get_logger() — structlog JSON logger
└── validation/
    ├── base_rule.py       ValidationRule / Severity dataclasses
    └── runner.py          run_validation() → (clean_df, quarantine_df, dq_results_df)
```

## Development

```bash
pip install -e ".[dev]"   # installs with test + lint extras
pytest tests/             # runs unit tests
ruff check .              # lint
```
