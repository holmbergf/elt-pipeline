#!/usr/bin/env bash
# Enable Basin Catalog on the ingestion bucket and print the values to put in .env.
# Terraform provider 5.x has no catalog resource, so this is a one-time CLI step.
set -euo pipefail
BUCKET="${1:-nfl-ingestion}"
echo "Enabling Basin Catalog on bucket: $BUCKET"
npx --yes wrangler basin catalog enable "$BUCKET"
echo
echo "Now create an R2 API token (Admin Read & Write) in the dashboard and set:"
echo "  BASIN_CATALOG_URI / BASIN_WAREHOUSE  (printed above)"
echo "  BASIN_TOKEN                          (the R2 token value)"
echo "Then create the Iceberg tables:"
echo "  source ../.venv/bin/activate && python -m elt_ingest.iceberg"
