
-- =====================================================
-- Walmart Data Engineering Project
-- Snowflake Environment Setup
-- =====================================================

USE ROLE ACCOUNTADMIN;

-- 1. Create Virtual Warehouse
CREATE WAREHOUSE IF NOT EXISTS WALMART_WH
    WAREHOUSE_TYPE = 'STANDARD'
    WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Compute warehouse for Walmart analytics';

-- 2. Create Database
CREATE DATABASE IF NOT EXISTS WALMART_ANALYTICS
    COMMENT = 'Walmart data engineering and analytics';

-- 3. Create Schemas
CREATE SCHEMA IF NOT EXISTS WALMART_ANALYTICS.RAW
    COMMENT = 'Original data ingested from AWS S3';

CREATE SCHEMA IF NOT EXISTS WALMART_ANALYTICS.STAGING
    COMMENT = 'Cleaned and standardized data from dbt';

CREATE SCHEMA IF NOT EXISTS WALMART_ANALYTICS.MARTS
    COMMENT = 'Analysis-ready tables produced by dbt';

-- 4. Set Context
USE WAREHOUSE WALMART_WH;
USE DATABASE WALMART_ANALYTICS;
USE SCHEMA RAW;

-- =====================================================
--Verification of Setup
-- =====================================================

-- View the warehouse
SHOW WAREHOUSES LIKE 'WALMART_WH';

-- View the database
SHOW DATABASES LIKE 'WALMART_ANALYTICS';

-- View the schemas
SHOW SCHEMAS IN DATABASE WALMART_ANALYTICS;

-- Check the current context
SELECT
    CURRENT_ROLE() AS CURRENT_ROLE,
    CURRENT_WAREHOUSE() AS CURRENT_WAREHOUSE,
    CURRENT_DATABASE() AS CURRENT_DATABASE,
    CURRENT_SCHEMA() AS CURRENT_SCHEMA;

-- =====================================================
--S3 Storage Integration
-- =====================================================

CREATE STORAGE INTEGRATION IF NOT EXISTS WALMART_S3_INTEGRATION
    TYPE = EXTERNAL_STAGE
    STORAGE_PROVIDER = 'S3'
    ENABLED = TRUE
    STORAGE_AWS_ROLE_ARN =
      'arn:aws:iam::727663801042:role/SnowflakeWalmartS3Role'
    STORAGE_ALLOWED_LOCATIONS =
      ('s3://walmart-analysis-raw-data/')
    COMMENT = 'Read-only access to Walmart raw data in S3';


-- =====================================================
-- Get AWS Info
-- =====================================================
DESC STORAGE INTEGRATION WALMART_S3_INTEGRATION;
