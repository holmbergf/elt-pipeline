"""Settings from environment. No secrets in code; see .env.example at repo root."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# data-integration/src/elt_ingest/config.py -> repo root is 4 parents up from src layout:
# elt_ingest/ -> src/ -> data-integration/ -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes")


@dataclass(frozen=True)
class Settings:
    storage_backend: str = "local"  # "r2" | "local"
    local_data_dir: Path = REPO_ROOT / "data" / "raw"
    r2_bucket: str = "nfl"
    ingestion_prefix: str = "ingestion"
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_endpoint_url: str = ""  # derived from account id when empty
    basin_catalog_uri: str = ""
    basin_warehouse: str = ""
    basin_token: str = ""
    basin_namespace: str = "nfl"

    @classmethod
    def from_env(cls) -> "Settings":
        account = os.getenv("R2_ACCOUNT_ID") or os.getenv("TF_VAR_cloudflare_account_id") or ""
        endpoint = os.getenv("R2_ENDPOINT_URL") or (
            f"https://{account}.r2.cloudflarestorage.com" if account else ""
        )
        backend = os.getenv("STORAGE_BACKEND", "").strip().lower()
        if not backend:
            backend = "r2" if (account and os.getenv("R2_ACCESS_KEY_ID")) else "local"
        return cls(
            storage_backend=backend,
            local_data_dir=Path(os.getenv("LOCAL_DATA_DIR", str(REPO_ROOT / "data" / "raw"))),
            r2_bucket=os.getenv("R2_BUCKET", "nfl"),
            ingestion_prefix=os.getenv("INGESTION_PREFIX", "ingestion").strip("/"),
            r2_account_id=account,
            r2_access_key_id=os.getenv("R2_ACCESS_KEY_ID", ""),
            r2_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY", ""),
            r2_endpoint_url=endpoint,
            basin_catalog_uri=os.getenv("BASIN_CATALOG_URI", ""),
            basin_warehouse=os.getenv("BASIN_WAREHOUSE", ""),
            basin_token=os.getenv("BASIN_TOKEN") or os.getenv("R2_API_TOKEN", ""),
            basin_namespace=os.getenv("BASIN_NAMESPACE", "nfl"),
        )

    def require_r2(self) -> None:
        missing = [
            n
            for n, v in (
                ("R2_ACCOUNT_ID", self.r2_account_id),
                ("R2_ACCESS_KEY_ID", self.r2_access_key_id),
                ("R2_SECRET_ACCESS_KEY", self.r2_secret_access_key),
            )
            if not v
        ]
        if missing:
            raise RuntimeError(
                f"STORAGE_BACKEND=r2 but missing env: {', '.join(missing)}. "
                "Create an R2 API token (Admin Read & Write) and set them in .env."
            )
