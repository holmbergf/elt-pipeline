# Contributing

Thanks for taking a look. This is a small project; keep changes focused
and covered by tests.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e "./data-integration[iceberg,dev]" dbt-duckdb duckdb
cp .env.example .env   # fill in values, never commit .env
```

Without R2 credentials, ingestion falls back to local storage under
`data/raw/` and the dbt dev target builds against that mirror, so most
development works offline. The dbt CI build uses committed mock raw
fixtures (`dbt-transform/tests/fixtures/`).

## Tests

Run the suites that cover what you touched:

```bash
python -m pytest data-integration/tests -q
python -m pytest dashboard/tests -q
cd dbt-transform && dbt build --profiles-dir .   # mock fixtures, dev target
```

Add or update a test with every behavior change: a focused pytest under
`data-integration/tests/` or `dashboard/tests/`, or a dbt schema/singular
test under `dbt-transform/`.

## Pull requests

- One concern per PR; describe what broke or changed and how you verified
  it (tests run, dbt build, manual check).
- CI is path-filtered: ingestion changes run `ci/data-integration`, dbt
  changes run `ci/dbt`, `infra/` changes run `ci/infra` (fmt + validate).
- Never commit credentials, `.env` files, Terraform state or variables
  with real values, or exported warehouse data. Use the `*.example`
  templates. If you think you committed a secret, say so in the PR —
  see `SECURITY.md`.

## Data sources

Game and market data come from nflverse, ESPN's public scoreboard API,
and Covers consensus pages. Respect those providers' terms when adding
or changing scrapers, and keep request rates modest.
