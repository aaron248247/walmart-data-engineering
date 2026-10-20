
SELECT
    STORE AS Store_id,
    DATE AS Store_Date,
    TEMPERATURE AS Store_temperature,
    FUEL_PRICE AS Fuel_price,
    MARKDOWN1 AS Markdown1,
    MARKDOWN2 AS Markdown2,
    MARKDOWN3 AS Markdown3,
    MARKDOWN4 AS Markdown4,
    MARKDOWN5 AS Markdown5,
    CPI AS CPI,
    UNEMPLOYMENT AS Unemployment,
    ISHOLIDAY AS IsHoliday
FROM {{ source('walmart_raw', 'fact_raw') }}
