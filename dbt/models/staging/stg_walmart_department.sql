
SELECT
    STORE AS Store_id,
    DEPT AS Dept_id,
    DATE AS Store_Date,
    WEEKLY_SALES AS Store_Weekly_sales,
    ISHOLIDAY AS IsHoliday
FROM {{ source('walmart_raw', 'department_raw') }}
