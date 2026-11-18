# Matchup Board (Streamlit) — NFL + NCAAF

Private, password-gated decision-support dashboard over the elt-pipeline
semantic layer (`semantic_upcoming_matchups`, `semantic_team_season_form`,
`semantic_game_results`). The sidebar Sport switcher gives NFL and NCAAF
their own section with identical pages; each reads its own bucket's exports
(`s3://nfl/...` / `s3://ncaaf/...`). The NCAAF Upcoming cards show AP Top-25
ranks. It presents statistics and market data for users to make their own
decisions — it does not recommend bets.

Pages: **Upcoming** (today/next slate: lines, consensus, side-by-side form),
**Team Form** (season explorer), **Trends** (per-team scoring/totals trends).

## Data path

DuckDB reads the published Parquet exports from R2:
`s3://nfl/data_warehouse/semantic/*.parquet` (published by
`elt_ingest.publish_warehouse` on the ingest schedule). Cached 1 hour.

## Deploy (Streamlit Community Cloud, free tier)

1. Push this repo to GitHub (already done: `holmbergf/elt-pipeline`).
2. share.streamlit.io → New app → repo `holmbergf/elt-pipeline`, branch
   `main`, main file `dashboard/streamlit_app.py`.
3. In the app's Settings → Secrets, paste the keys from
   `.streamlit/secrets.toml.example` with real values:
   `app_password`, `r2_access_key_id`, `r2_secret_access_key`,
   `r2_s3_host`, `r2_bucket`, `r2_bucket_ncaaf`.
   Use a read-only R2 token (Object Read) for the app.
4. Deploy. The repo stays private; the app additionally requires the
   password.

## Local run

```bash
source .venv/bin/activate
pip install -r dashboard/requirements.txt
# either R2 env vars, or a local mirror of the exports:
LOCAL_WAREHOUSE_DIR=/path/to/dir-containing-data_warehouse \
  streamlit run dashboard/streamlit_app.py
```
