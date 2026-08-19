#!/usr/bin/env python3
"""Generate medium-sized synthetic credit application data for the workshop."""

import argparse
import csv
import math
import random
from pathlib import Path


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def poisson_like(rng: random.Random, lam: float, cap: int = 12) -> int:
    """Simple Poisson draw without numpy (Python 3.12+ compatible)."""
    p = 1.0 - math.exp(-lam)
    count = 0
    while count < cap and rng.random() < p:
        count += 1
    return count


def generate_row(applicant_id: int, rng: random.Random) -> dict:
    utilization = min(10.0, max(0.0, rng.betavariate(2, 5) * 1.5))
    age = rng.randint(22, 74)
    delinq_30_59 = poisson_like(rng, 0.4, cap=8)
    delinq_60_89 = poisson_like(rng, 0.2, cap=6)
    delinq_90 = poisson_like(rng, 0.15, cap=6)
    debt_ratio = min(5.0, max(0.0, rng.lognormvariate(0.2, 0.6)))

    income_missing = rng.random() < 0.18
    monthly_income = None if income_missing else round(rng.lognormvariate(8.6, 0.55), 2)

    open_lines = poisson_like(rng, 8.0, cap=30)
    real_estate = poisson_like(rng, 1.5, cap=10)

    dependents = None if rng.random() < 0.03 else float(poisson_like(rng, 1.0, cap=8))

    income_for_model = monthly_income if monthly_income is not None else 4500.0
    logit = (
        -4.2
        + 1.1 * utilization
        + 0.75 * delinq_30_59
        + 1.0 * delinq_90
        + 0.35 * debt_ratio
        - 0.00005 * income_for_model
        + (0.25 if income_missing else 0.0)
        - 0.012 * age
    )
    default_flag = 1 if rng.random() < sigmoid(logit) else 0

    return {
        "Id": applicant_id,
        "SeriousDlqin2yrs": default_flag,
        "RevolvingUtilizationOfUnsecuredLines": round(utilization, 6),
        "age": age,
        "NumberOfTime30-59DaysPastDueNotWorse": delinq_30_59,
        "DebtRatio": round(debt_ratio, 6),
        "MonthlyIncome": monthly_income if monthly_income is not None else "",
        "NumberOfOpenCreditLinesAndLoans": open_lines,
        "NumberOfTimes90DaysLate": delinq_90,
        "NumberRealEstateLoansOrLines": real_estate,
        "NumberOfTime60-89DaysPastDueNotWorse": delinq_60_89,
        "NumberOfDependents": dependents if dependents is not None else "",
    }


FIELDNAMES = [
    "Id",
    "SeriousDlqin2yrs",
    "RevolvingUtilizationOfUnsecuredLines",
    "age",
    "NumberOfTime30-59DaysPastDueNotWorse",
    "DebtRatio",
    "MonthlyIncome",
    "NumberOfOpenCreditLinesAndLoans",
    "NumberOfTimes90DaysLate",
    "NumberRealEstateLoansOrLines",
    "NumberOfTime60-89DaysPastDueNotWorse",
    "NumberOfDependents",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=40_000, help="Number of applicants (default: 40000)")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "cs-training.csv")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    defaults = 0

    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for i in range(1, args.rows + 1):
            row = generate_row(i, rng)
            defaults += row["SeriousDlqin2yrs"]
            writer.writerow(row)

    size_mb = args.output.stat().st_size / 1_024 / 1_024
    print(f"Wrote {args.rows:,} rows to {args.output}")
    print(f"File size: {size_mb:.2f} MB")
    print(f"Default rate: {defaults / args.rows:.2%}")


if __name__ == "__main__":
    main()
