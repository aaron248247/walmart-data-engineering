-- =====================================================
-- Walmart Data Engineering Project
-- Raw Ingestion
-- =====================================================

-- =====================================================
-- Create File Format for CSV Inport
-- =====================================================

-- Set Active Role/Warehouse/Database/Schema

USE ROLE ACCOUNTADMIN;
USE WAREHOUSE WALMART_WH;
USE DATABASE WALMART_ANALYTICS;
USE SCHEMA RAW;

CREATE FILE FORMAT IF NOT EXISTS WALMART_CSV_INSPECTION
    TYPE = CSV
    FIELD_DELIMITER = ','
    SKIP_HEADER = 0
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    TRIM_SPACE = TRUE;



-- Preview File Contents


-- Preview department.csv
SELECT
    $1, $2, $3, $4, $5, $6
FROM @WALMART_ANALYTICS.RAW.WALMART_S3_STAGE/department.csv
    (FILE_FORMAT => 'WALMART_ANALYTICS.RAW.WALMART_CSV_INSPECTION')
LIMIT 5;

-- Preview fact.csv
SELECT
    $1, $2, $3, $4, $5, $6, $7,
    $8, $9, $10, $11, $12
FROM @WALMART_ANALYTICS.RAW.WALMART_S3_STAGE/fact.csv
    (FILE_FORMAT => 'WALMART_ANALYTICS.RAW.WALMART_CSV_INSPECTION')
LIMIT 50;

-- Preview stores.csv
SELECT
    $1, $2, $3
FROM @WALMART_ANALYTICS.RAW.WALMART_S3_STAGE/stores.csv
    (FILE_FORMAT => 'WALMART_ANALYTICS.RAW.WALMART_CSV_INSPECTION')
LIMIT 5;


-- =====================================================
-- Create Tables
-- Note:  Using Number(#,#) instead of Float for value comparison without floating point differences
-- =====================================================

CREATE TABLE IF NOT EXISTS DEPARTMENT_RAW (
    STORE NUMBER(10,0),
    DEPT NUMBER(10,0),  
    DATE DATE,
    WEEKLY_SALES NUMBER(18,2),
    ISHOLIDAY BOOLEAN
);

CREATE TABLE IF NOT EXISTS FACT_RAW (
    STORE NUMBER(10,0),
    DATE DATE,
    TEMPERATURE NUMBER(10,2),
    FUEL_PRICE NUMBER(12,2),
    MARKDOWN1 NUMBER(18,2),
    MARKDOWN2 NUMBER(18,2),
    MARKDOWN3 NUMBER(18,2),
    MARKDOWN4 NUMBER(18,2),
    MARKDOWN5 NUMBER(18,2),
    CPI NUMBER(18,7),
    UNEMPLOYMENT NUMBER(10,3),
    ISHOLIDAY BOOLEAN
);

CREATE TABLE IF NOT EXISTS STORE_RAW (
    STORE NUMBER(10,0),
    TYPE VARCHAR(5),
    SIZE NUMBER(12,0)
);

-- =====================================================
-- Create File Format for Loading
-- =====================================================

CREATE FILE FORMAT IF NOT EXISTS WALMART_CSV_LOAD
    TYPE = CSV
    FIELD_DELIMITER = ','
    SKIP_HEADER = 1
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    TRIM_SPACE = TRUE
    EMPTY_FIELD_AS_NULL = TRUE
    NULL_IF = ('NA', 'NULL', '');

-- =====================================================
-- Copy data into raw tables
-- =====================================================

--Load department.csv
COPY INTO WALMART_ANALYTICS.RAW.DEPARTMENT_RAW
FROM @WALMART_ANALYTICS.RAW.WALMART_S3_STAGE
FILES = ('department.csv')
FILE_FORMAT = (
    FORMAT_NAME = WALMART_ANALYTICS.RAW.WALMART_CSV_lOAD
)
ON_ERROR = ABORT_STATEMENT;

--Load fact.csv
COPY INTO WALMART_ANALYTICS.RAW.FACT_RAW
FROM @WALMART_ANALYTICS.RAW.WALMART_S3_STAGE
FILES = ('fact.csv')
FILE_FORMAT = (
    FORMAT_NAME = WALMART_ANALYTICS.RAW.WALMART_CSV_lOAD
)
ON_ERROR = ABORT_STATEMENT;

--Load store.csv
COPY INTO WALMART_ANALYTICS.RAW.STORE_RAW
FROM @WALMART_ANALYTICS.RAW.WALMART_S3_STAGE
FILES = ('stores.csv')
FILE_FORMAT = (
    FORMAT_NAME = WALMART_ANALYTICS.RAW.WALMART_CSV_lOAD
)
ON_ERROR = ABORT_STATEMENT;

-- =====================================================
-- Validate tables
-- =====================================================

--Verify Counts
SELECT 'DEPARTMENT' AS TABLE_NAME, COUNT(*) AS ROW_COUNT
FROM WALMART_ANALYTICS.RAW.DEPARTMENT_RAW

UNION

SELECT 'FACT' AS TABLE_NAME, COUNT(*) AS ROW_COUNT
FROM WALMART_ANALYTICS.RAW.FACT_RAW

UNION

SELECT 'STORE' AS TABLE_NAME, COUNT(*) AS ROW_COUNT
FROM WALMART_ANALYTICS.RAW.STORE_RAW;

--Verify data

select * 
from WALMART_ANALYTICS.Raw.DEPARTMENT_RAW
limit 10;

select * 
from WALMART_ANALYTICS.Raw.fact_RAW
limit 10;

select * 
from WALMART_ANALYTICS.Raw.store_RAW
limit 10;