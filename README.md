
# Walmart Data Engineering and Analytics

## Project Overview

An end-to-end data engineering project using AWS S3,
Snowflake, dbt, and Python to ingest, transform,
analyze, and visualize Walmart data.

## Architecture

AWS S3
  → Snowflake Storage Integration
  → Snowflake RAW Tables
  → dbt Transformations
  → Snowflake Analytics Tables
  → Python Visualizations

## Technologies

- AWS S3: Raw data storage
- AWS IAM: Secure access management
- Snowflake: Cloud data warehouse
- dbt: Data transformation and testing
- Python: Data analysis and visualization
- GitHub: Version control and documentation

## Project Structure

- aws/ - AWS infrastructure documentation
- snowflake/ - SQL scripts and ingestion
- dbt/ - Transformation models and tests
- python/ - Visualization scripts
- notebooks/ - Exploratory analysis
- figures/ - Generated visualizations
- docs/ - Technical documentation

## Current Status

- [x] AWS S3 bucket created and populated
- [x] AWS IAM read policy created
- [x] AWS IAM role created
- [x] Snowflake storage integration configured
- [x] Data loaded into Snowflake
- [x] dbt transformations implemented
- [x] Python visualizations completed
