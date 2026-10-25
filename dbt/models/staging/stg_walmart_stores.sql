
SELECT
    STORE AS STORE_ID,
    TYPE AS STORE_TYPE,
    SIZE AS STORE_SIZE
FROM {{ source('walmart_raw', 'store_raw') }}
