"""Storage: partitioned Parquet in R2 (or local dir) + JSON run manifests.

Layout in the bucket / local dir:
  raw/nfl/games/season=<season>/part-<content_hash>.parquet
  raw/nfl/spreads/event_date=<date>/part-<content_hash>.parquet
  raw/nfl/totals/event_date=<date>/part-<content_hash>.parquet
  _manifests/nfl/<dataset>/<run_id>.json

Keys are content-addressed, so re-running the same scrape is a no-op
(idempotent) instead of appending duplicates on re-runs.
Manifests are the watermark/state store (Step 3): they record covered dates,
max game date and row counts per run; this is the pipeline's only state store.
"""

from __future__ import annotations

import io
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .clean import content_hash
from .config import Settings

log = logging.getLogger(__name__)

DATASETS = ("games", "spreads", "totals")
# Zone inside the bucket: ingestion/raw/nfl/... and ingestion/_manifests/nfl/...
DEFAULT_PREFIX = "ingestion"


@dataclass
class WriteResult:
    dataset: str
    keys: list[str] = field(default_factory=list)
    skipped_keys: list[str] = field(default_factory=list)
    rows: int = 0
    covered_dates: list[str] = field(default_factory=list)
    max_date: str | None = None


class LocalStorage:
    """Filesystem backend for dev/tests (same key layout as R2)."""

    def __init__(self, root: Path, prefix: str = DEFAULT_PREFIX, sport: str = "nfl"):
        self.root = Path(root)
        self.prefix = prefix
        self.sport = sport

    def _path(self, key: str) -> Path:
        return self.root / key

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def put_bytes(self, key: str, data: bytes) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def get_bytes(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def list_keys(self, prefix: str) -> list[str]:
        base = self._path(prefix)
        if not base.exists():
            return []
        return sorted(str(p.relative_to(self.root)) for p in base.rglob("*") if p.is_file())


class R2Storage:
    """R2 via its S3-compatible API (boto3)."""

    def __init__(self, settings: Settings):
        settings.require_r2()
        self.prefix = settings.ingestion_prefix
        self.sport = getattr(settings, "sport", "nfl")
        import boto3
        from botocore.config import Config

        self.bucket = settings.r2_bucket
        self._s3 = boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint_url,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name="auto",
            config=Config(retries={"max_attempts": 5, "mode": "standard"}),
        )

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self._s3.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("404", "NoSuchKey"):
                return False
            raise

    def put_bytes(self, key: str, data: bytes) -> None:
        self._s3.put_object(Bucket=self.bucket, Key=key, Body=data)

    def get_bytes(self, key: str) -> bytes:
        return self._s3.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def list_keys(self, prefix: str) -> list[str]:
        keys, token = [], None
        while True:
            kw = dict(Bucket=self.bucket, Prefix=prefix)
            if token:
                kw["ContinuationToken"] = token
            page = self._s3.list_objects_v2(**kw)
            keys += [o["Key"] for o in page.get("Contents", [])]
            if not page.get("IsTruncated"):
                return sorted(keys)
            token = page["NextContinuationToken"]


def get_storage(settings: Settings, sport: str = "nfl", bucket: str | None = None):
    from dataclasses import replace

    if bucket or sport != "nfl":
        settings = replace(settings, r2_bucket=bucket or settings.r2_bucket, sport=sport)
    return R2Storage(settings) if settings.storage_backend == "r2" else LocalStorage(settings.local_data_dir, settings.ingestion_prefix, sport)


def _partition_groups(df: pd.DataFrame, dataset: str):
    if dataset == "games" and "season" in df.columns:
        for season, part in df.groupby("season"):
            yield f"season={int(season)}", part
    elif dataset in ("spreads", "totals") and "event_date" in df.columns:
        for date, part in df.groupby(df["event_date"].astype(str).str[:10]):
            yield f"event_date={date}", part
    else:
        yield "all", df


def write_dataset(storage, df: pd.DataFrame, dataset: str, source: str) -> WriteResult:
    """Write df as content-addressed Parquet partitions + one run manifest."""
    if dataset not in DATASETS:
        raise ValueError(f"unknown dataset {dataset!r}, expected one of {DATASETS}")
    result = WriteResult(dataset=dataset, rows=len(df))
    if df.empty:
        return result
    date_col = "date" if dataset == "games" else "event_date"
    if date_col in df.columns:
        dates = sorted(df[date_col].astype(str).str[:10].unique())
        result.covered_dates = dates
        result.max_date = dates[-1] if dates else None
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + content_hash(df)
    for partition, part in _partition_groups(df, dataset):
        buf = io.BytesIO()
        part.to_parquet(buf, index=False)
        # Hash without the import timestamp: identical data re-fetched later
        # must map to the same key (idempotent), not a new version per run.
        hash_part = part.drop(columns=["timestamp_imported"], errors="ignore")
        key = f"{storage.prefix}/raw/{storage.sport}/{dataset}/{partition}/part-{content_hash(hash_part)}.parquet"
        if storage.exists(key):
            result.skipped_keys.append(key)
            continue
        storage.put_bytes(key, buf.getvalue())
        result.keys.append(key)
    manifest = {
        "run_id": run_id,
        "dataset": dataset,
        "source": source,
        "written_at": datetime.now(timezone.utc).isoformat(),
        "rows": result.rows,
        "keys": result.keys,
        "skipped_keys": result.skipped_keys,
        "covered_dates": result.covered_dates,
        "max_date": result.max_date,
        "content_hash": content_hash(df),
    }
    storage.put_bytes(f"{storage.prefix}/_manifests/{storage.sport}/{dataset}/{run_id}.json", json.dumps(manifest, indent=2).encode())
    log.info("wrote %s: %d rows, %d new objects, %d skipped", dataset, result.rows, len(result.keys), len(result.skipped_keys))
    return result


class StateStore:
    """Watermarks derived from run manifests."""

    def __init__(self, storage):
        self.storage = storage

    def manifests(self, dataset: str) -> list[dict]:
        out = []
        for key in self.storage.list_keys(f"{self.storage.prefix}/_manifests/{self.storage.sport}/{dataset}/"):
            if key.endswith(".json"):
                out.append(json.loads(self.storage.get_bytes(key)))
        return out

    def game_dates(self) -> list[str]:
        dates: set[str] = set()
        for m in self.manifests("games"):
            dates.update(m.get("covered_dates") or [])
        return sorted(dates)

    def max_game_date(self) -> str | None:
        dates = self.game_dates()
        return dates[-1] if dates else None

    def covered_dates(self, dataset: str) -> set[str]:
        dates: set[str] = set()
        for m in self.manifests(dataset):
            dates.update(m.get("covered_dates") or [])
        return dates

    def missing_dates(self, dataset: str, since_days: int | None = None) -> list[str]:
        """Game dates with no spreads/totals manifest yet (newest first)."""
        dates = self.game_dates()
        if since_days is not None and dates:
            # Anchor at today, not the max game date: the schedule includes future fixtures.
            today = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
            cutoff = (pd.Timestamp(today) - pd.Timedelta(days=since_days)).strftime("%Y-%m-%d")
            dates = [d for d in dates if cutoff <= d <= today]
        covered = self.covered_dates(dataset)
        return sorted((d for d in dates if d not in covered), reverse=True)
