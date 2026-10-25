--This test is to ensure that the store_id and store_date combination in the stg_walmart_fact table is unique.
SELECT
    STORE_ID,
    STORE_DATE,
    COUNT(*) AS row_count
FROM {{ ref('stg_walmart_fact') }}
GROUP BY
    STORE_ID,
    STORE_DATE
HAVING COUNT(*) > 1
