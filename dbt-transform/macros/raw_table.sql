{# Raw relation: Basin Catalog Iceberg table when BASIN_DUCKDB_CATALOG is
   set (an ATTACHed DuckDB Iceberg catalog), otherwise the partitioned Parquet
   raw zone written by elt-ingest (local data/raw or an s3:// R2 prefix).
   Sport selects the bucket layout: raw/<sport>/... under RAW_BASE_PATH
   (nfl) or RAW_BASE_PATH_NCAAF. #}
{% macro raw_table(dataset, sport='nfl') %}
  {%- set tbl = {'games': 'raw_' ~ sport ~ '_games', 'spreads': 'raw_' ~ sport ~ '_spreads', 'totals': 'raw_' ~ sport ~ '_totals'}[dataset] -%}
  {%- set catalog = env_var('BASIN_DUCKDB_CATALOG', '') -%}
  {%- if catalog -%}
    {{ catalog }}.{{ sport }}.{{ tbl }}
  {%- elif sport == 'ncaaf' -%}
    (select * from read_parquet('{{ env_var('RAW_BASE_PATH_NCAAF', '../data/raw-ncaaf/ingestion') }}/raw/ncaaf/{{ dataset }}/**/*.parquet', hive_partitioning=true, union_by_name=true))
  {%- else -%}
    (select * from read_parquet('{{ env_var('RAW_BASE_PATH', '../data/raw/ingestion') }}/raw/nfl/{{ dataset }}/**/*.parquet', hive_partitioning=true, union_by_name=true))
  {%- endif -%}
{% endmacro %}
