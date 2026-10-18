-- =====================================================
-- Walmart Data Engineering Project
-- Create External Stage
-- =====================================================
CREATE STAGE IF NOT EXISTS
    WALMART_ANALYTICS.RAW.WALMART_S3_STAGE
    URL = 's3://walmart-analysis-raw-data/'
    STORAGE_INTEGRATION = WALMART_S3_INTEGRATION
    COMMENT = 'External stage for Walmart raw data';

-- =====================================================
-- Test External Stage
-- =====================================================

LIST @WALMART_ANALYTICS.RAW.WALMART_S3_STAGE;



-- =====================================================