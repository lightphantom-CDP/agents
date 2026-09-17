#!/usr/bin/env bash
# Source this file on the Data Hub edge/gateway node before running jobs.
#   source datahub/env.workshopdelh.sh

export CREDIT_CATALOG="${CREDIT_CATALOG:-hive}"
export CREDIT_DATABASE="${CREDIT_DATABASE:-credit_demo}"
export RAW_BASE_PATH="${RAW_BASE_PATH:-s3a://lhdemocdpbca1/credit-demo/raw}"
export FEATURE_VERSION="${FEATURE_VERSION:-v1}"
export SCRIPT_BASE="${SCRIPT_BASE:-s3a://lhdemocdpbca1/credit-demo/cde}"

# Optional: override if scripts are on local disk instead of S3
# export SCRIPT_BASE="/home/cloudbreak/credit-demo/cde"

echo "CREDIT_CATALOG=$CREDIT_CATALOG"
echo "CREDIT_DATABASE=$CREDIT_DATABASE"
echo "RAW_BASE_PATH=$RAW_BASE_PATH"
echo "SCRIPT_BASE=$SCRIPT_BASE"
