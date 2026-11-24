# Matchup Board (Streamlit) — NFL + NCAAF

Decision-support dashboard over the elt-pipeline warehouse. The sidebar
Sport switcher gives NFL and NCAAF their own section with identical
pages; each reads its own bucket's published exports. It presents
statistics and market data for users to make their own decisions — it
does not recommend bets.

**Live board:** <!-- TODO: replace with the deployed Streamlit app URL -->
_deploy the app (below) and link its URL here._

Pages:

- **Upcoming** — today's / next slate: lines, consensus, side-by-side
  form, plus a historical-games view using the same matchup card.
- **Team Form** — season explorer with rankings.
- **Trends** — per-team scoring and totals trends.
- **Consensus** — cover/win rates by consensus band and line bucket
  ("All seasons" aggregates every season).

## Data path

DuckDB reads the published Parquet exports from R2
(`data_warehouse/semantic/*.parquet`, plus the silver
`fct_*_betting_upcoming` / `fct_*_betting_settled` fixtures), published
by `elt_ingest.publish_warehouse` on the ingest schedule. Loaded frames
are cached for an hour, keyed on a warehouse version stamp that is
re-probed every minute — so a fresh publish shows up within ~60s
without restarting the app. The Upcoming page filters fixtures to the
current Pacific date at read time, so a build-day game is never shown
as today's game on a later day.

## Access

The board is public and read-only by default. It reads R2 with a
**read-only** token (Object Read) held server-side in Streamlit
secrets — visitors never see credentials. To gate the board instead,
set `app_password` in the app's secrets; see
`.streamlit/secrets.toml.example`.

## Deploy (Streamlit Community Cloud, free tier)

1. share.streamlit.io → New app → this repository, branch `main`,
   main file `dashboard/streamlit_app.py`.
2. In the app's Settings → Secrets, paste the keys from
   `.streamlit/secrets.toml.example` with real values. The app deploys
   directly from this repo; pushes to `main` redeploy automatically.
3. Add the resulting app URL above (and as the GitHub repo homepage).

## Local run

```bash
source .venv/bin/activate
pip install -r dashboard/requirements.txt
# either R2 credentials in .streamlit/secrets.toml / env vars, or a
# local mirror of the published exports:
LOCAL_WAREHOUSE_DIR=/path/to/dir-containing-data_warehouse \
  streamlit run dashboard/streamlit_app.py
```

The local mirror layout is `<dir>/data_warehouse/...` for NFL and
`<dir>/ncaaf/data_warehouse/...` for NCAAF.
