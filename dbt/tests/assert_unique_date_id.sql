-- This tests the uniqueness of the date_id in walmart_date_dim
SELECT date_id, COUNT(*) AS row_count
FROM {{ ref('walmart_date_dim') }}
GROUP BY date_id
HAVING COUNT(*) > 1