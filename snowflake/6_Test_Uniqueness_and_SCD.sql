-- =====================================================
-- Walmart Data Engineering Project
-- Test Uniqueness and SCD1 and SCD2
-- =====================================================



USE WAREHOUSE WALMART_WH;
USE DATABASE WALMART_ANALYTICS;
USE SCHEMA MARTS;



SELECT *
FROM WALMART_ANALYTICS.MARTS.STG_WALMART_STORES
ORDER BY STORE_ID;

SELECT * FROM WALMART_ANALYTICS.MARTS.WALMART_STORE_DIM;


SELECT
    COUNT(*)                                  AS total_rows,
    COUNT(DISTINCT store_id)                  AS stores,
    COUNT(DISTINCT store_id || '-' || dept_id) AS store_dept_pairs,
    COUNT_IF(dept_id IS NULL)                 AS null_dept_rows
FROM WALMART_ANALYTICS.MARTS.WALMART_STORE_DIM;


-- =====================================================
-- Walmart Data Engineering Project
-- Testing SCD1 for walmart_store_dim.sql and walmart_date_dim.sql
-- =====================================================


--Test walmart_store_dim.sql 
--Expected:  2 changed rows
CREATE OR REPLACE TRANSIENT TABLE WALMART_ANALYTICS.MARTS.STORE_DIM_AUDIT_CHECK AS
SELECT store_id, DEPT_ID, store_type, store_size, insert_date, update_date
FROM WALMART_ANALYTICS.MARTS.WALMART_STORE_DIM;


UPDATE WALMART_ANALYTICS.MARTS.WALMART_STORE_DIM
SET STORE_SIZE = STORE_SIZE + 1000
WHERE STORE_ID = 1 AND DEPT_ID = 1;

DELETE FROM WALMART_ANALYTICS.MARTS.WALMART_STORE_DIM
WHERE STORE_ID = 2 AND DEPT_ID = 1;


SELECT
    cur.store_id,
    cur.dept_id,
    prev.store_size  AS original_size,
    cur.store_size   AS current_size,
    prev.insert_date AS old_insert, cur.insert_date AS new_insert,
    prev.update_date AS old_update, cur.update_date AS new_update
FROM WALMART_ANALYTICS.MARTS.WALMART_STORE_DIM cur
JOIN WALMART_ANALYTICS.MARTS.STORE_DIM_AUDIT_CHECK prev
  ON cur.store_id = prev.store_id
  and cur.dept_id = prev.dept_id
WHERE cur.store_id IN (1, 2);

-- Expect 2: only stores 1 and 2 changed
SELECT COUNT(*) AS changed_rows
FROM WALMART_ANALYTICS.MARTS.WALMART_STORE_DIM cur
JOIN WALMART_ANALYTICS.MARTS.STORE_DIM_AUDIT_CHECK prev
  ON cur.store_id = prev.store_id
  and cur.dept_id = prev.dept_id
WHERE cur.insert_date IS DISTINCT FROM prev.insert_date
   OR cur.update_date IS DISTINCT FROM prev.update_date;
-- Only 2 changed rows




--Test walmart_date_dim.sql 
--Expected:  2 changed rows
CREATE OR REPLACE TRANSIENT TABLE WALMART_ANALYTICS.MARTS.DATE_DIM_AUDIT_CHECK AS
SELECT DATE_ID, STORE_DATE, IShOLIDAY, INSERT_DATE, UPDATE_DATE
FROM WALMART_ANALYTICS.MARTS.WALMART_DATE_DIM;


UPDATE WALMART_ANALYTICS.MARTS.WALMART_DATE_DIM
SET ISHOLIDAY = NOT ISHOLIDAY
WHERE DATE_ID = 1;

DELETE FROM WALMART_ANALYTICS.MARTS.WALMART_DATE_DIM
WHERE DATE_ID = 2;


SELECT
    cur.DATE_id,

    prev.STORE_dATE  AS original_DATE,
    cur.store_DATE   AS current_DATE,
    prev.insert_date AS old_insert, cur.insert_date AS new_insert,
    prev.update_date AS old_update, cur.update_date AS new_update
FROM WALMART_ANALYTICS.MARTS.WALMART_DATE_DIM cur
JOIN WALMART_ANALYTICS.MARTS.DATE_DIM_AUDIT_CHECK prev
  ON cur.DATE_id = prev.DATE_id

WHERE cur.DATE_id IN (1, 2);

-- Expect 2: only stores 1 and 2 changed
SELECT COUNT(*) AS changed_rows
FROM WALMART_ANALYTICS.MARTS.WALMART_DATE_DIM cur
JOIN WALMART_ANALYTICS.MARTS.DATE_DIM_AUDIT_CHECK prev
  ON cur.DATE_id = prev.DATE_id

WHERE cur.insert_date IS DISTINCT FROM prev.insert_date
   OR cur.update_date IS DISTINCT FROM prev.update_date;
-- Only 2 changed rows


-- =====================================================
-- Walmart Data Engineering Project
-- Testing SCD2 for walmart_fact_table.sql
-- =====================================================

DESCRIBE TABLE WALMART_ANALYTICS.MARTS.WALMART_FACT_TABLE;

SELECT COUNT(*) FROM WALMART_ANALYTICS.MARTS.WALMART_FACT_TABLE;
--Row Count = 421,570 - first build
--Row Count = 421,570 - second build


-- Test the SCD2 table by updating the weekly sales in the Department_Raw table

UPDATE WALMART_ANALYTICS.RAW.DEPARTMENT_RAW
SET WEEKLY_SALES = WEEKLY_SALES + 100
WHERE STORE = 1 AND DEPT = 1
  AND DATE = (SELECT MIN(DATE) FROM WALMART_ANALYTICS.RAW.DEPARTMENT_RAW WHERE STORE = 1 AND DEPT = 1);


  SELECT STORE_ID, DEPT_ID, DATE_ID, STORE_WEEKLY_SALES,
       VRSN_START_DATE, VRSN_END_DATE, INSERT_DATE, UPDATE_DATE
FROM WALMART_ANALYTICS.MARTS.WALMART_FACT_TABLE
WHERE STORE_ID = 1 AND DEPT_ID = 1
  AND DATE_ID = (SELECT MIN(DATE_ID) FROM WALMART_ANALYTICS.MARTS.WALMART_FACT_TABLE
                 WHERE STORE_ID = 1 AND DEPT_ID = 1)
ORDER BY VRSN_START_DATE;

--Two rows exist for this row, with the weekly sales incremented by 100

--Second check - increase fuel price in the fact_raw table
UPDATE  WALMART_ANALYTICS.RAW.FACT_RAW
SET FUEL_PRICE = FUEL_PRICE + 1
WHERE STORE = 1
  AND DATE = (SELECT MIN(DATE) FROM  WALMART_ANALYTICS.RAW.FACT_RAW WHERE STORE = 1);

    SELECT STORE_ID, DEPT_ID, DATE_ID, FUEL_PRICE,
       VRSN_START_DATE, VRSN_END_DATE, INSERT_DATE, UPDATE_DATE
FROM WALMART_ANALYTICS.MARTS.WALMART_FACT_TABLE
WHERE STORE_ID = 1 AND DEPT_ID = 1
  AND DATE_ID = (SELECT MIN(DATE_ID) FROM WALMART_ANALYTICS.MARTS.WALMART_FACT_TABLE
                 WHERE STORE_ID = 1 AND DEPT_ID = 1)
ORDER BY VRSN_START_DATE;

--Reset the Raw tables back to their respective values