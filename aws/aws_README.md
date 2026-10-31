# AWS infrastructure

This directory documents the AWS resources used by the Walmart data engineering project to stage raw data for Snowflake.

## S3 bucket

| Setting | Current value |
|---|---|
| Bucket | `walmart-analysis-raw-data` |
| Region | `us-east-1` |
| Versioning | Not enabled. `GetBucketVersioning` returned no status. |
| Bucket policy | None attached. `GetBucketPolicy` returned `NoSuchBucketPolicy`. |
| Default encryption | Not documented yet. |
| S3 Block Public Access | Not documented yet. |

A missing bucket policy does not by itself establish whether the bucket is accessible. Review the IAM role's permissions and the bucket's public-access settings to understand access.

## Snowflake access through IAM

Snowflake uses the storage integration `WALMART_S3_INTEGRATION` to access the S3 bucket. The integration's configured AWS role ARN and allowed S3 locations should be verified in Snowflake with:

```sql
DESC INTEGRATION WALMART_S3_INTEGRATION;
```

| Setting | Value |
|---|---|
| IAM role name | `[Record the role name from STORAGE_AWS_ROLE_ARN]` |
| IAM role ARN | `[Redact the AWS account ID in shared documentation]` |
| Snowflake integration allowed locations | `[Record STORAGE_ALLOWED_LOCATIONS]` |

### Trust relationship

The IAM role trust policy allows a Snowflake AWS principal to call `sts:AssumeRole`, conditioned on a Snowflake external ID. The account-specific principal ARN and external ID are redacted here.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "<REDACTED_SNOWFLAKE_AWS_PRINCIPAL_ARN>"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "<REDACTED_SNOWFLAKE_EXTERNAL_ID>"
        }
      }
    }
  ]
}
```

This redacted policy is for documentation only; the placeholders are not valid values for deploying the policy.

### IAM permission policies

The role has attached policy metadata (policy name and ARN) and may also have inline policies. Record the actual S3 actions and resource ARNs from the policy documents here; those details have not yet been captured in this README.

| Policy type | Policy name | Policy ARN | S3 actions and resource scope |
|---|---|---|---|
| Attached managed policy | `[Record from list-attached-role-policies]` | `[Record or redact account ID]` | `[Document from policy JSON]` |
| Inline policy | `[Record if present]` | Not applicable | `[Document from policy JSON]` |

## Verification commands

Run these with AWS CLI credentials that can read the relevant resources. Exported configuration can include account-specific identifiers; review it before adding it to Git or sharing it.

```powershell
aws s3api get-bucket-location --bucket walmart-analysis-raw-data --output json
aws s3api get-bucket-versioning --bucket walmart-analysis-raw-data --output json
aws s3api get-bucket-policy --bucket walmart-analysis-raw-data --output json
aws s3api get-bucket-encryption --bucket walmart-analysis-raw-data --output json
aws s3api get-public-access-block --bucket walmart-analysis-raw-data --output json

aws iam get-role --role-name <ROLE_NAME> --output json
aws iam list-attached-role-policies --role-name <ROLE_NAME> --output json
aws iam list-role-policies --role-name <ROLE_NAME> --output json
```

To retrieve an inline role policy document:

```powershell
aws iam get-role-policy --role-name <ROLE_NAME> --policy-name <POLICY_NAME> --output json
```

For a customer-managed attached policy, retrieve its default version's policy document using `get-policy` and `get-policy-version`.

## Security notes

- Do not commit AWS access keys, secret access keys, session tokens, private keys, or local AWS credential files.
- Keep the actual trust policy and Snowflake external ID in AWS/Snowflake configuration. Use redacted values in shared documentation or exported archives.
- This README describes observed configuration; it is not infrastructure-as-code and does not recreate the resources.
