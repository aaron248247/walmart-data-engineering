--This test ensures that the store_id in stg_walmart_department is unique.

SELECT DISTINCT
    department.STORE_ID
FROM {{ref('stg_walmart_department')}} AS department
LEFT JOIN {{ref('stg_walmart_stores')}} AS stores 
    ON department.STORE_ID = stores.STORE_ID
where stores.STORE_ID IS NULL