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
        STORE_DATE,
        ISHOLIDAY
       
    FROM {{ ref('stg_walmart_fact') }} 

),

final AS (

    SELECT 
        SOURCE.DATE_ID,
        source.STORE_DATE,
        source.ISHOLIDAY,

        {% if is_incremental() %}

        COALESCE(existing.INSERT_DATE, CURRENT_TIMESTAMP()) AS INSERT_DATE,

        CASE
            WHEN existing.STORE_DATE IS DISTINCT FROM source.STORE_DATE
              OR existing.ISHOLIDAY IS DISTINCT FROM source.ISHOLIDAY
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
        ON  source.DATE_ID = existing.DATE_ID

    {% endif %}

)

SELECT * FROM final