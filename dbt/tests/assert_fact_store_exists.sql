--This test ensures that the store_id in stg_walmart_stores is unique.
SELECT DISTINCT
    fact.store_id
FROM {{ref('stg_walmart_fact')}} AS fact 
LEFT JOIN {{ref('stg_walmart_stores')}} AS stores 
    ON fact.store_id = stores.store_id
WHERE stores.store_id IS NULL