-- This tests the uniqueness of the date_id in walmart_date_dim
SELECT DATE_ID, COUNT(*) AS row_count
FROM {{ ref('walmart_date_dim') }}
GROUP BY DATE_ID
HAVING COUNT(*) > 1