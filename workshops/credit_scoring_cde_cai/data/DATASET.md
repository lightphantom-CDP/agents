# Workshop dataset — Give Me Some Credit format

## Included file

| File | Rows | Size | Description |
|------|------|------|-------------|
| **`cs-training.csv`** | 40,000 | ~2 MB | Medium synthetic credit dataset |

**Why 40,000 rows?**
- Large enough for meaningful ML metrics (AUC, risk bands)
- Small enough for fast CDE jobs in a workshop (~2–5 min ingest)
- Full Kaggle dataset has ~150k rows (~8 MB) — fine for production, slow for demos

## Schema (matches Kaggle Give Me Some Credit)

Same column names as the original so all workshop scripts work unchanged:

```
Id, SeriousDlqin2yrs, RevolvingUtilizationOfUnsecuredLines, age,
NumberOfTime30-59DaysPastDueNotWorse, DebtRatio, MonthlyIncome,
NumberOfOpenCreditLinesAndLoans, NumberOfTimes90DaysLate,
NumberRealEstateLoansOrLines, NumberOfTime60-89DaysPastDueNotWorse,
NumberOfDependents
```

- **Label:** `SeriousDlqin2yrs` (1 = default, 0 = no default)
- **Missing values:** `MonthlyIncome`, `NumberOfDependents` (~18% / ~3% null)
- **Default rate:** ~6–8% (realistic for credit risk)

## How to use in CDE

### Option A — Upload to data lake (recommended)

```bash
aws s3 cp cs-training.csv s3://<your-bucket>/workshop/credit_scoring/landing/cs-training.csv
```

CDE ingest job parameter:
```
--db workshop_credit --landing s3a://<your-bucket>/workshop/credit_scoring/landing
```

### Option B — Upload to CDE Resources

1. CDE → Resources → Upload `cs-training.csv`
2. Point ingest job to the resource path (environment-specific)

## Regenerate different sizes

```bash
cd workshops/credit_scoring_cde_cai/data
python3 generate_sample_data.py --rows 20000   # smaller (~1 MB)
python3 generate_sample_data.py --rows 40000   # medium (default)
python3 generate_sample_data.py --rows 80000   # larger (~4 MB)
```

## Alternative sizes

| Rows | Size | Best for |
|------|------|----------|
| 10,000 | ~0.5 MB | Quick smoke test |
| **40,000** | **~2 MB** | **Workshop default** |
| 80,000 | ~4 MB | Larger audience / performance demo |
| 150,000 | ~8 MB | Kaggle original scale |
