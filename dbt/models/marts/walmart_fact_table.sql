{{
    config(
        materialized='incremental',
        unique_key=['STORE_ID', 'DEPT_ID', 'DATE_ID', 'VRSN_START_DATE'],
        incremental_strategy='merge',
        on_schema_change='fail',
        merge_exclude_columns=['INSERT_DATE']
    )
}}

WITH run_metadata AS (
    SELECT CURRENT_TIMESTAMP()::TIMESTAMP_NTZ AS RUN_TS
),

departments AS (
    SELECT DISTINCT
        swd.STORE_ID,
        swd.DEPT_ID,
        wdd.DATE_ID,
        swd.STORE_WEEKLY_SALES,
        swd.STORE_DATE
    FROM {{ ref('stg_walmart_department') }} AS swd
    INNER JOIN {{ ref('walmart_date_dim') }} AS wdd
        ON swd.STORE_DATE = wdd.STORE_DATE
),

source_data AS (
    SELECT
        swd.STORE_ID,
        swd.DEPT_ID,
        swd.DATE_ID,
        wsd.STORE_SIZE,
        swd.STORE_WEEKLY_SALES,
        swf.FUEL_PRICE,
        swf.STORE_TEMPERATURE AS TEMPERATURE,
        swf.UNEMPLOYMENT,
        swf.CPI,
        swf.MARKDOWN1,
        swf.MARKDOWN2,
        swf.MARKDOWN3,
        swf.MARKDOWN4,
        swf.MARKDOWN5
    FROM {{ ref('stg_walmart_fact') }} AS swf
    INNER JOIN departments AS swd
        ON swf.STORE_ID = swd.STORE_ID
        AND swf.STORE_DATE = swd.STORE_DATE
    LEFT JOIN {{ ref('walmart_store_dim') }} AS wsd
        ON swf.STORE_ID = wsd.STORE_ID
        AND swd.DEPT_ID  = wsd.DEPT_ID
)       

{% if is_incremental() %}

, current_rows AS (
    SELECT *
    FROM {{ this }}
    WHERE VRSN_END_DATE IS NULL
),

table_metadata AS (
    SELECT COALESCE(MIN(INSERT_DATE), (SELECT RUN_TS FROM run_metadata)) AS TABLE_INSERT_DATE
    FROM {{ this }}
),


changed_rows AS (
    SELECT
        src.*,
        current_rows.VRSN_START_DATE AS OLD_VRSN_START_DATE,
        current_rows.INSERT_DATE AS ORIGINAL_INSERT_DATE
    FROM source_data AS src
    INNER JOIN current_rows
        ON src.STORE_ID = current_rows.STORE_ID
        AND src.DEPT_ID = current_rows.DEPT_ID
        AND src.DATE_ID = current_rows.DATE_ID
    WHERE
        src.STORE_SIZE IS DISTINCT FROM current_rows.STORE_SIZE
        OR src.STORE_WEEKLY_SALES IS DISTINCT FROM current_rows.STORE_WEEKLY_SALES
        OR src.FUEL_PRICE IS DISTINCT FROM current_rows.FUEL_PRICE
        OR src.TEMPERATURE IS DISTINCT FROM current_rows.TEMPERATURE
        OR src.UNEMPLOYMENT IS DISTINCT FROM current_rows.UNEMPLOYMENT
        OR src.CPI IS DISTINCT FROM current_rows.CPI
        OR src.MARKDOWN1 IS DISTINCT FROM current_rows.MARKDOWN1
        OR src.MARKDOWN2 IS DISTINCT FROM current_rows.MARKDOWN2
        OR src.MARKDOWN3 IS DISTINCT FROM current_rows.MARKDOWN3
        OR src.MARKDOWN4 IS DISTINCT FROM current_rows.MARKDOWN4
        OR src.MARKDOWN5 IS DISTINCT FROM current_rows.MARKDOWN5
),

closed_versions AS (
    SELECT
        old.STORE_ID,
        old.DEPT_ID,
        old.DATE_ID,
        old.STORE_SIZE,
        old.STORE_WEEKLY_SALES,
        old.FUEL_PRICE,
        old.TEMPERATURE,
        old.UNEMPLOYMENT,
        old.CPI,
        old.MARKDOWN1,
        old.MARKDOWN2,
        old.MARKDOWN3,
        old.MARKDOWN4,
        old.MARKDOWN5,
        old.VRSN_START_DATE,
        run_metadata.RUN_TS AS VRSN_END_DATE,
        old.INSERT_DATE,
        run_metadata.RUN_TS AS UPDATE_DATE
    FROM current_rows AS old
    INNER JOIN changed_rows AS changed
        ON old.STORE_ID = changed.STORE_ID
        AND old.DEPT_ID = changed.DEPT_ID
        AND old.DATE_ID = changed.DATE_ID
        AND old.VRSN_START_DATE = changed.OLD_VRSN_START_DATE
    CROSS JOIN run_metadata
),

new_versions AS (
    SELECT
        changed.STORE_ID,
        changed.DEPT_ID,
        changed.DATE_ID,
        changed.STORE_SIZE,
        changed.STORE_WEEKLY_SALES,
        changed.FUEL_PRICE,
        changed.TEMPERATURE,
        changed.UNEMPLOYMENT,
        changed.CPI,
        changed.MARKDOWN1,
        changed.MARKDOWN2,
        changed.MARKDOWN3,
        changed.MARKDOWN4,
        changed.MARKDOWN5,
        run_metadata.RUN_TS AS VRSN_START_DATE,
        CAST(NULL AS TIMESTAMP_NTZ) AS VRSN_END_DATE,
        changed.ORIGINAL_INSERT_DATE AS INSERT_DATE,
        run_metadata.RUN_TS AS UPDATE_DATE
    FROM changed_rows AS changed
    CROSS JOIN run_metadata
),

new_keys AS (
    SELECT src.*
    FROM source_data AS src
    LEFT JOIN current_rows
        ON src.STORE_ID = current_rows.STORE_ID
        AND src.DEPT_ID = current_rows.DEPT_ID
        AND src.DATE_ID = current_rows.DATE_ID
    WHERE current_rows.STORE_ID IS NULL
),

first_versions AS (
    SELECT
        new_keys.STORE_ID,
        new_keys.DEPT_ID,
        new_keys.DATE_ID,
        new_keys.STORE_SIZE,
        new_keys.STORE_WEEKLY_SALES,
        new_keys.FUEL_PRICE,
        new_keys.TEMPERATURE,
        new_keys.UNEMPLOYMENT,
        new_keys.CPI,
        new_keys.MARKDOWN1,
        new_keys.MARKDOWN2,
        new_keys.MARKDOWN3,
        new_keys.MARKDOWN4,
        new_keys.MARKDOWN5,
        run_metadata.RUN_TS AS VRSN_START_DATE,
        CAST(NULL AS TIMESTAMP_NTZ) AS VRSN_END_DATE,
        table_metadata.TABLE_INSERT_DATE AS INSERT_DATE,
        run_metadata.RUN_TS AS UPDATE_DATE
    FROM new_keys
    CROSS JOIN run_metadata
    CROSS JOIN table_metadata
)

SELECT * FROM closed_versions
UNION ALL
SELECT * FROM new_versions
UNION ALL
SELECT * FROM first_versions

{% else %}

SELECT
    source_data.STORE_ID,
    source_data.DEPT_ID,
    source_data.DATE_ID,
    source_data.STORE_SIZE,
    source_data.STORE_WEEKLY_SALES,
    source_data.FUEL_PRICE,
    source_data.TEMPERATURE,
    source_data.UNEMPLOYMENT,
    source_data.CPI,
    source_data.MARKDOWN1,
    source_data.MARKDOWN2,
    source_data.MARKDOWN3,
    source_data.MARKDOWN4,
    source_data.MARKDOWN5,
    run_metadata.RUN_TS AS VRSN_START_DATE,
    CAST(NULL AS TIMESTAMP_NTZ) AS VRSN_END_DATE,
    run_metadata.RUN_TS AS INSERT_DATE,
    run_metadata.RUN_TS AS UPDATE_DATE
FROM source_data
CROSS JOIN run_metadata

{% endif %}