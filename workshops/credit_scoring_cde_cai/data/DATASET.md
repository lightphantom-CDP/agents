# Workshop dataset — Give Me Some Credit

## Source

Download from Kaggle: [Give Me Some Credit](https://www.kaggle.com/c/GiveMeSomeCredit/data)

Primary file: `cs-training.csv` (~150k rows)

## Columns (original)

| Column | Description |
|--------|-------------|
| `Id` | Applicant identifier |
| `SeriousDlqin2yrs` | **Label** — 1 if 90+ DPD in 2 years, else 0 |
| `RevolvingUtilizationOfUnsecuredLines` | Credit utilization ratio |
| `age` | Age in years |
| `NumberOfTime30-59DaysPastDueNotWorse` | 30–59 DPD count |
| `DebtRatio` | Monthly debt / monthly income |
| `MonthlyIncome` | Monthly income (nullable) |
| `NumberOfOpenCreditLinesAndLoans` | Open credit lines |
| `NumberOfTimes90DaysLate` | 90+ DPD count |
| `NumberRealEstateLoansOrLines` | Real estate loans |
| `NumberOfTime60-89DaysPastDueNotWorse` | 60–89 DPD count |
| `NumberOfDependents` | Dependents (nullable) |

## Facilitator setup — upload to data lake

Replace placeholders with your environment values:

```bash
# Example: AWS S3 landing zone
export WORKSHOP_BUCKET=s3a://your-datalake-bucket/workshop/credit_scoring
aws s3 cp cs-training.csv ${WORKSHOP_BUCKET}/landing/cs-training.csv

# Or upload via CDP Data Hub / cloud console to:
#   s3a://<bucket>/workshop/credit_scoring/landing/cs-training.csv
```

## Workshop table naming convention

All tables use database `workshop_credit` (create in your catalog):

| Table | Purpose |
|-------|---------|
| `workshop_credit.raw_applications` | Raw CSV as ingested |
| `workshop_credit.features` | Engineered features + label |
| `workshop_credit.scores` | Model output |
| `workshop_credit.quality_log` | Data quality run results |

## Synthetic data (fallback)

If Kaggle is unavailable, generate a small synthetic dataset in CDE Lab 1 using the provided `generate_synthetic_data()` function in `labs/01_ingest_raw.py`.
