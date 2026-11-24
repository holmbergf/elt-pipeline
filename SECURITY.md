# Security policy

## Reporting a vulnerability

Please do not open a public issue for security problems. Use GitHub's
private vulnerability reporting (Security → Report a vulnerability) on
this repository, or contact the maintainer privately.

Reports of leaked credentials in this repo are especially welcome —
include the file/commit you found them in, but not the secret itself.

## Handling credentials

- All credentials live outside the repo: `.env` locally, GitHub Actions
  secrets in CI, and Streamlit secrets for the dashboard. Only
  `*.example` templates are committed.
- The dashboard must use a **read-only** R2 token (Object Read),
  scoped to the `nfl`/`ncaaf` buckets. Never put write credentials in
  Streamlit secrets.
- Ingestion/publish tokens should be scoped to the two warehouse
  buckets and rotated if exposed.
- `infra/backend.hcl` (Terraform state endpoint, includes the account
  ID) is gitignored; use `infra/backend.hcl.example` as the template.

If you fork this project, create your own tokens and buckets — nothing
in this repository grants access to the maintainer's infrastructure.
