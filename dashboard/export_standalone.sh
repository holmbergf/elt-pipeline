#!/usr/bin/env bash
# Export the dashboard as a standalone repo (app at root) for Streamlit Cloud.
# The live Matchup Board deploys from fholmberg/nfl-dashboard, NOT from this
# repo — after changing dashboard/, re-run this export and push there, or the
# deployed app keeps serving the old build.
# Usage: ./dashboard/export_standalone.sh /path/to/nfl-dashboard-checkout
set -euo pipefail
DEST="${1:?usage: export_standalone.sh <destination-dir>}"
mkdir -p "$DEST/.streamlit"
cp dashboard/streamlit_app.py dashboard/data.py dashboard/requirements.txt "$DEST/"
cp dashboard/.streamlit/secrets.toml.example dashboard/.streamlit/config.toml "$DEST/.streamlit/"
cat > "$DEST/README.md" <<'MD'
# Matchup Board (NFL + NCAAF)

Streamlit dashboard over the elt-pipeline semantic layer.
Sidebar switches between the NFL and NCAAF sections (same pages, each
sport reads its own R2 bucket: `nfl` / `ncaaf`).
Reads published Parquet exports from Cloudflare R2 (read-only keys in
Streamlit secrets). Presents statistics and market data for users to make
their own decisions; it does not recommend bets.

Live: https://dzzheeqfpuy774nutwccl2.streamlit.app/

Deploy: Streamlit Community Cloud -> main file `streamlit_app.py`.
Secrets: see `.streamlit/secrets.toml.example` (`app_password` optional;
without it the board is public read-only).

Note: this is a standalone export for Streamlit Cloud. The source of
truth is `dashboard/` in https://github.com/holmbergf/elt-pipeline —
re-copy `streamlit_app.py`, `data.py`, `requirements.txt`, and
`.streamlit/*` from there when updating.
MD
cat > "$DEST/.gitignore" <<'GI'
.streamlit/secrets.toml
__pycache__/
GI
echo "Exported standalone dashboard to $DEST"
