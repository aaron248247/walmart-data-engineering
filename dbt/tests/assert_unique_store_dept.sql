--This test is to ensure that the store_id, dept_id is unique.
SELECT
    STORE_ID,
    DEPT_ID,
    COUNT(*) AS row_count
FROM {{ ref('walmart_store_dim') }}
GROUP BY
    STORE_ID,
    DEPT_ID
HAVING COUNT(*) > 1
