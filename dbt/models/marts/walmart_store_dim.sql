{{
    config(
        materialized='incremental',
        unique_key=['store_id', 'dept_id'],
        incremental_strategy='merge',
        on_schema_change='fail',
        merge_exclude_columns=['insert_date']
    )
}}

WITH departments AS (

    SELECT DISTINCT
        store_id,
        dept_id
    FROM {{ ref('stg_walmart_department') }}

),

source_data AS (

    SELECT
        sws.store_id,
        swd.dept_id,
        sws.store_type,
        sws.store_size
    FROM {{ ref('stg_walmart_stores') }} AS sws
    INNER JOIN departments AS swd
        ON sws.store_id = swd.store_id

),

final AS (

    SELECT
        source.store_id,
        source.dept_id,
        source.store_type,
        source.store_size,

        {% if is_incremental() %}

        COALESCE(existing.insert_date, CURRENT_TIMESTAMP()) AS insert_date,

        CASE
            WHEN existing.store_id IS NULL
              OR existing.store_type IS DISTINCT FROM source.store_type
              OR existing.store_size IS DISTINCT FROM source.store_size
            THEN CURRENT_TIMESTAMP()
            ELSE existing.update_date
        END AS update_date

        {% else %}

        CURRENT_TIMESTAMP() AS insert_date,
        CURRENT_TIMESTAMP() AS update_date

        {% endif %}

    FROM source_data AS source

    {% if is_incremental() %}
    LEFT JOIN {{ this }} AS existing
        ON  source.store_id = existing.store_id
        AND source.dept_id  = existing.dept_id
    {% endif %}

)

SELECT * FROM final