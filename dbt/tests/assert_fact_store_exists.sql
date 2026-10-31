--This test ensures that the store_id in stg_walmart_stores is unique.
SELECT DISTINCT
    fact.STORE_ID
FROM {{ref('stg_walmart_fact')}} AS fact 
LEFT JOIN {{ref('stg_walmart_stores')}} AS stores 
    ON fact.STORE_ID = stores.STORE_ID
WHERE stores.STORE_ID IS NULL