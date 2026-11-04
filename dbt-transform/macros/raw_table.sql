{# Raw NFL relation: Basin Catalog Iceberg table when BASIN_DUCKDB_CATALOG is
   set (an ATTACHed DuckDB Iceberg catalog), otherwise the partitioned Parquet
   raw zone written by elt-ingest (local data/raw or an s3:// R2 prefix). #}
{% macro raw_table(dataset) %}
  {%- set tbl = {'games': 'raw_nfl_games', 'spreads': 'raw_nfl_spreads', 'totals': 'raw_nfl_totals'}[dataset] -%}
  {%- set catalog = env_var('BASIN_DUCKDB_CATALOG', '') -%}
  {%- if catalog -%}
    {{ catalog }}.{{ env_var('BASIN_NAMESPACE', 'nfl') }}.{{ tbl }}
  {%- else -%}
    (select * from read_parquet('{{ env_var('RAW_BASE_PATH', '../data/raw/ingestion') }}/raw/nfl/{{ dataset }}/**/*.parquet', hive_partitioning=true, union_by_name=true))
  {%- endif -%}
{% endmacro %}
