
SELECT
    Store_id,
    Dept_id,
    Store_Date,
    COUNT(*) AS row_count
FROM {{ ref('stg_walmart_department') }}
GROUP BY
    Store_id,
    Dept_id,
    Store_Date
HAVING COUNT(*) > 1
