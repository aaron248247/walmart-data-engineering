
SELECT
    STORE AS Store_id,
    TYPE AS Store_type,
    SIZE AS Store_size
FROM {{ source('walmart_raw', 'store_raw') }}
