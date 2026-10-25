{{
    config(
        materialized='incremental',
        unique_key=['STORE_ID','DEPT_ID', 'DATE_ID'],
        incremental_strategy='merge',
        on_schema_change='fail',
        merge_exclude_columns=['insert_date']
    )
}}

WITH departments AS (

    SELECT DISTINCT
        swd.STORE_ID,
        swd.DEPT_ID,
        wdd.DATE_ID,
        swd.STORE_WEEKLY_SALES,
        swd.STORE_DATE
    FROM {{ ref('stg_walmart_department') }} as swd
    
    INNER JOIN {{ref('walmart_date_dim')}} as wdd 
    ON swd.STORE_DATE = wdd.STORE_DATE

),


source_data AS (

    SELECT
        swd.STORE_ID,
        swd.DEPT_ID,
        swd.DATE_ID,
        swd.STORE_WEEKLY_SALES,
        swf.FUEL_PRICE,
        swf.STORE_TEMPERATURE,
        swf.UNEMPLOYMENT,
        swf.CPI,
        swf.MARKDOWN1 AS MARKDOWN1,
        swf.MARKDOWN2 AS MARKDOWN2,
        swf.MARKDOWN3 AS MARKDOWN3,
        swf.MARKDOWN4 AS MARKDOWN4,
        swf.MARKDOWN5 AS MARKDOWN5,
    FROM {{ ref('stg_walmart_fact') }} AS swf
    INNER JOIN departments AS swd
        ON swf.STORE_ID = swd.STORE_ID
        and swf.STORE_DATE = swd.STORE_DATE

)

select * from source_data