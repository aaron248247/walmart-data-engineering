{{
    config(
        materialized='incremental',
        unique_key=['date_id'],
        incremental_strategy='merge',
        on_schema_change='fail',
        merge_exclude_columns=['insert_date']
    )
}}


WITH source_data AS (

    SELECT DISTINCT
        DENSE_RANK() OVER (ORDER BY STORE_DATE) AS DATE_ID,
        store_date,
        IsHoliday
       
    FROM {{ ref('stg_walmart_fact') }} 

),

final AS (

    SELECT 
        SOURCE.DATE_ID,
        source.store_date,
        source.IsHoliday,

        {% if is_incremental() %}

        COALESCE(existing.insert_date, CURRENT_TIMESTAMP()) AS insert_date,

        CASE
            WHEN existing.store_date IS DISTINCT FROM source.store_date
              OR existing.IsHoliday IS DISTINCT FROM source.IsHoliday
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
        ON  source.date_id = existing.date_id

    {% endif %}

)

SELECT * FROM final