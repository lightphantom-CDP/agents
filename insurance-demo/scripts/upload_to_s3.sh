#!/usr/bin/env bash
# Upload insurance-demo CSVs to your CDP S3 bucket (AWS).
# Usage:
#   ./scripts/upload_to_s3.sh              # flat layout (Trino)
#   ./scripts/upload_to_s3.sh --impala-layout  # subfolder per table (Impala)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUCKET="${INSURANCE_S3_BUCKET:-s3://lhdemocdpbca1}"
PREFIX="${INSURANCE_S3_PREFIX:-insurancedemo/raw}"
IMPALA_LAYOUT=0

if [[ "${1:-}" == "--impala-layout" ]]; then
  IMPALA_LAYOUT=1
fi

if [[ ! -f "${ROOT}/data/claims.csv" ]]; then
  echo "No data found. Run: python3 scripts/generate_dummy_data.py"
  exit 1
fi

DEST="${BUCKET}/${PREFIX}"
echo "Uploading CSVs to ${DEST}/"

if [[ "${IMPALA_LAYOUT}" -eq 1 ]]; then
  echo "Layout: Impala (one subfolder per table)"
  aws s3 cp "${ROOT}/data/members.csv"          "${DEST}/members/members.csv"
  aws s3 cp "${ROOT}/data/policies.csv"         "${DEST}/policies/policies.csv"
  aws s3 cp "${ROOT}/data/medical_history.csv"  "${DEST}/medical_history/medical_history.csv"
  aws s3 cp "${ROOT}/data/claims.csv"           "${DEST}/claims/claims.csv"
  aws s3 cp "${ROOT}/data/claim_diagnoses.csv"  "${DEST}/claim_diagnoses/claim_diagnoses.csv"
  aws s3 cp "${ROOT}/data/claim_procedures.csv" "${DEST}/claim_procedures/claim_procedures.csv"
  aws s3 cp "${ROOT}/data/hospital_bills.csv"   "${DEST}/hospital_bills/hospital_bills.csv"
else
  echo "Layout: flat (Trino)"
  aws s3 cp "${ROOT}/data/members.csv"          "${DEST}/members.csv"
  aws s3 cp "${ROOT}/data/policies.csv"         "${DEST}/policies.csv"
  aws s3 cp "${ROOT}/data/medical_history.csv"  "${DEST}/medical_history.csv"
  aws s3 cp "${ROOT}/data/claims.csv"           "${DEST}/claims.csv"
  aws s3 cp "${ROOT}/data/claim_diagnoses.csv"  "${DEST}/claim_diagnoses.csv"
  aws s3 cp "${ROOT}/data/claim_procedures.csv" "${DEST}/claim_procedures.csv"
  aws s3 cp "${ROOT}/data/hospital_bills.csv"   "${DEST}/hospital_bills.csv"
fi

aws s3 cp "${ROOT}/data/policy/coverage_policy.md" "${BUCKET}/insurancedemo/policy/coverage_policy.md"

echo ""
echo "Done. Verify:"
echo "  aws s3 ls ${DEST}/ --recursive"
echo ""
echo "S3 base: s3a://lhdemocdpbca1/insurancedemo/raw"
