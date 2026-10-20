--This test ensures that the store_id in stg_walmart_department is unique.

SELECT DISTINCT
    department.store_id
FROM {{ref('stg_walmart_department')}} AS department
LEFT JOIN {{ref('stg_walmart_stores')}} AS stores 
    ON department.store_id = stores.store_id
where stores.store_id IS NULL