"""Publish must never silently write the dashboard's Parquet exports to
local disk: in CI the publish step once lacked STORAGE_BACKEND/R2_ACCOUNT_ID,
so exports landed on the ephemeral runner while the catalog publish logged
success — the dashboard stayed frozen at the last local publish."""

from pathlib import Path

import pytest

from elt_ingest.config import Settings
from elt_ingest.publish_warehouse import publish


def test_publish_rejects_local_storage(tmp_path):
    settings = Settings(storage_backend="local", basin_catalog_uri="https://example.invalid")
    with pytest.raises(RuntimeError, match="STORAGE_BACKEND"):
        publish(tmp_path / "warehouse.duckdb", settings=settings)


def test_ingest_workflow_publish_step_uses_r2_storage():
    workflow = (Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ingest.yml").read_text()
    publish_step = workflow.split("dbt build (prod) and publish warehouse tables", 1)[1]
    assert "STORAGE_BACKEND: r2" in publish_step
    assert "R2_ACCOUNT_ID:" in publish_step
