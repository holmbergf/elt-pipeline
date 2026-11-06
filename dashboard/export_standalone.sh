#!/usr/bin/env bash
# Export the dashboard as a standalone repo (app at root) for Streamlit Cloud.
# Usage: ./dashboard/export_standalone.sh /path/to/nfl-dashboard-checkout
set -euo pipefail
DEST="${1:?usage: export_standalone.sh <destination-dir>}"
mkdir -p "$DEST/.streamlit"
cp dashboard/streamlit_app.py dashboard/data.py dashboard/requirements.txt "$DEST/"
cp dashboard/.streamlit/secrets.toml.example dashboard/.streamlit/config.toml "$DEST/.streamlit/"
cat > "$DEST/README.md" <<'MD'
# Matchup Board (NFL + NCAAF)

Private-use Streamlit dashboard over the elt-pipeline semantic layer.
Sidebar switches between the NFL and NCAAF sections (same pages, each
sport reads its own R2 bucket: `nfl` / `ncaaf`).
Reads published Parquet exports from Cloudflare R2 (read-only keys in
Streamlit secrets). Presents statistics and market data for users to make
their own decisions; it does not recommend bets.

Deploy: Streamlit Community Cloud -> main file `streamlit_app.py`.
Secrets: see `.streamlit/secrets.toml.example`.
MD
cat > "$DEST/.gitignore" <<'GI'
.streamlit/secrets.toml
__pycache__/
GI
echo "Exported standalone dashboard to $DEST"
