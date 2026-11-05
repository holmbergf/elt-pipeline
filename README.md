# elt-pipeline

Cloudflare-based ELT (Extract, Load, Transform) data pipeline for NFL data ingestion and analytics.

## Architecture & Storage

- **Object Storage**: Cloudflare R2 bucket (`nfl`) with `ingestion/` and `data_warehouse/` zones for the data lake and warehouse.
- **Ingestion**: Python package in [`data-integration/`](data-integration/) — nflverse games + Covers spreads/totals, partitioned Parquet in R2, Basin Catalog Iceberg tables (`nfl.raw_nfl_*`). State lives in R2 run manifests. See [`.env.example`](.env.example).
- **Infrastructure as Code**: Terraform configurations located in [`infra/`](infra/).
- **Data Transformation**: dbt project located in [`dbt-transform/`](dbt-transform/) (powered by **dbt v2** `2.0.11` with built-in DuckDB engine).

## Project Structure

```text
elt-pipeline/
├── infra/                  # Terraform infrastructure definitions
│   ├── main.tf             # Cloudflare resources (R2 buckets, etc.)
│   ├── variables.tf        # Input variable declarations
│   ├── outputs.tf          # Resource outputs
│   ├── versions.tf         # Terraform and provider constraints
│   ├── terraform.tfvars.example # Template for variable overrides
│   └── README.md           # Infrastructure documentation
├── dbt-transform/          # dbt transformation project
│   ├── dbt_project.yml     # Project configuration (enforces dbt >=2.0.0)
│   ├── profiles.yml        # Local profile config (DuckDB adapter)
│   ├── models/             # SQL models and schemas
│   │   └── connector/nfl/  # NFL domain models
│   │       ├── sources.yml # Raw source definitions
│   │       ├── bronze/     # Raw extraction staging views
│   │       ├── silver/     # Cleaned dimensions, facts & staging
│   │       └── gold/       # Analytical marts and KPIs
│   ├── seeds/              # CSV seed data (nfl_team_mappings.csv)
│   ├── analyses/           # Ad-hoc analytical queries
│   ├── macros/             # Jinja macros
│   ├── snapshots/          # Point-in-time snapshots
│   └── tests/              # Custom data tests
├── .cursor/mcp.json        # MCP server configuration for Cursor
├── .vscode/mcp.json        # MCP server configuration for VS Code
├── .gitignore              # Git ignore rules (secrets, state, logs)
└── README.md
```

## Autonomous operation (GitHub Actions)

- `.github/workflows/nfl-ingest.yml` runs every Tuesday 11:17 UTC (and on
  manual dispatch): `elt-ingest all` → `dbt build --target prod` → publish
  silver/gold Iceberg tables. It is the production entry point.
- `.github/workflows/ci.yml` runs on push/PR: ingestion `pytest`, `dbt parse`,
  and Terraform `fmt`/`validate` (never `apply`).
- Terraform is applied manually from `infra/`; state stays local and is
  git-ignored. Do not add `terraform apply` to CI without first moving state
  to a remote backend.

### Required GitHub Secrets

| Secret | Source |
|---|---|
| `R2_ACCOUNT_ID` | Cloudflare account ID |
| `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` | R2 API token S3 credentials |
| `R2_S3_HOST` | `<account-id>.r2.cloudflarestorage.com` |
| `BASIN_CATALOG_URI` / `BASIN_WAREHOUSE` | `terraform -chdir=infra output` |
| `BASIN_TOKEN` | R2 API token value (catalog permission) |
| `CLOUDFLARE_API_TOKEN` | Only for manual Terraform runs, not used by workflows |

Local development uses the same variable names via `.env` (see
`.env.example`); `.env` is git-ignored and must never be committed.
