
{{ config(
    materialized='table'
) }}

with date_spine as (
    -- Bounds from vars: start_year (default 2015) to current year + 1
    select
        cast('{{ var("start_year", 2015) }}-01-01' as date) + (interval '1 day' * i) as date_day
    from range(0, 6000) t(i)
    where cast('{{ var("start_year", 2015) }}-01-01' as date) + (interval '1 day' * i) <= cast((extract(year from current_date)::int + 1)::varchar || '-12-31' as date)
)

select
    md5(cast(date_day as varchar)) as date_id,
    date_day,
    extract(year from date_day) as year,
    extract(month from date_day) as month,
    extract(day from date_day) as day,
    extract(quarter from date_day) as quarter,
    dayname(date_day) as day_name,
    monthname(date_day) as month_name,
    case when extract(dow from date_day) in (0, 6) then true else false end as is_weekend,
    -- NFL specific flags
    case when extract(dow from date_day) = 0 then true else false end as is_nfl_sunday,
    case when extract(dow from date_day) = 1 then true else false end as is_nfl_monday,
    case when extract(dow from date_day) = 4 then true else false end as is_nfl_thursday
from date_spine
