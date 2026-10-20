--This test is to ensure that the store_id and store_date combination in the stg_walmart_fact table is unique.
SELECT
    Store_id,
    Store_Date,
    COUNT(*) AS row_count
FROM {{ ref('stg_walmart_fact') }}
GROUP BY
    Store_id,
    Store_Date
HAVING COUNT(*) > 1
