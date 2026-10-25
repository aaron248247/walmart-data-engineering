
SELECT
    STORE_ID,
    DEPT_ID,
    STORE_DATE,
    COUNT(*) AS row_count
FROM {{ ref('stg_walmart_department') }}
GROUP BY
    STORE_ID,
    DEPT_ID,
    STORE_DATE
HAVING COUNT(*) > 1
