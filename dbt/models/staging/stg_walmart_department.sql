
SELECT
    STORE AS STORE_ID,
    DEPT AS DEPT_ID,
    DATE AS STORE_DATE,
    WEEKLY_SALES AS STORE_WEEKLY_SALES,
    ISHOLIDAY 
FROM {{ source('walmart_raw', 'department_raw') }}
