FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install ".[iceberg]"

# Incremental NFL ingestion (games -> spreads -> totals). State lives in R2
# manifests, so the container is stateless. Trigger on a schedule with
# Cloudflare Containers / Cron, GitHub Actions, or any cron host:
#   docker run --env-file .env elt-ingest
ENTRYPOINT ["elt-ingest"]
CMD ["all"]
