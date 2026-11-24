# Matchup Board (Streamlit) — NFL + NCAAF

Decision-support dashboard over the elt-pipeline warehouse. The sidebar
Sport switcher gives NFL and NCAAF their own section with identical
pages; each reads its own bucket's published exports. It presents
statistics and market data for users to make their own decisions — it
does not recommend bets.

**Live board:** https://dzzheeqfpuy774nutwccl2.streamlit.app/

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

The live board deploys from the standalone export repo
([fholmberg/nfl-dashboard](https://github.com/fholmberg/nfl-dashboard),
app at its root), **not** from this repository — pushes here do not
redeploy it. To ship a dashboard change to the live board:

```bash
./dashboard/export_standalone.sh /path/to/nfl-dashboard-checkout
cd /path/to/nfl-dashboard-checkout && git add -A && git commit -m "..." && git push
```

Streamlit Cloud then redeploys automatically (or use Manage app →
Reboot app). In the app's Settings → Secrets, paste the keys from
`.streamlit/secrets.toml.example` with real values.

For your own deployment you can equally point Streamlit Cloud at this
repository directly (branch `main`, main file
`dashboard/streamlit_app.py`) and skip the standalone export.

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
