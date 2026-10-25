{{
    config(
        materialized='incremental',
        unique_key=['STORE_ID', 'DEPT_ID'],
        incremental_strategy='merge',
        on_schema_change='fail',
        merge_exclude_columns=['INSERT_DATE']
    )
}}

WITH departments AS (

    SELECT DISTINCT
        STORE_ID,
        DEPT_ID
    FROM {{ ref('stg_walmart_department') }}

),

source_data AS (

    SELECT
        sws.STORE_ID,
        swd.DEPT_ID,
        sws.STORE_TYPE,
        sws.STORE_SIZE
    FROM {{ ref('stg_walmart_stores') }} AS sws
    INNER JOIN departments AS swd
        ON sws.STORE_ID = swd.STORE_ID

),

final AS (

    SELECT
        source.STORE_ID,
        source.DEPT_ID,
        source.STORE_TYPE,
        source.STORE_SIZE,

        {% if is_incremental() %}

        COALESCE(existing.INSERT_DATE, CURRENT_TIMESTAMP()) AS INSERT_DATE,

        CASE
            WHEN existing.STORE_ID IS NULL
              OR existing.STORE_TYPE IS DISTINCT FROM source.STORE_TYPE
              OR existing.sSTORE_SIZE IS DISTINCT FROM source.STORE_SIZE
            THEN CURRENT_TIMESTAMP()
            ELSE existing.UPDATE_DATE
        END AS UPDATE_DATE

        {% else %}

        CURRENT_TIMESTAMP() AS INSERT_DATE,
        CURRENT_TIMESTAMP() AS UPDATE_DATE

        {% endif %}

    FROM source_data AS source

    {% if is_incremental() %}
    LEFT JOIN {{ this }} AS existing
        ON  source.STORE_ID = existing.STORE_ID
        AND source.DEPT_ID  = existing.DEPT_ID
    {% endif %}

)

SELECT * FROM final