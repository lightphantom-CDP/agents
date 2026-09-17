#!/usr/bin/env python3
"""Generate synthetic credit demo datasets for the CDE + Cloudera AI workshop."""

from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
POLICY_DIR = DATA_DIR / "policy"

RNG = random.Random(42)

APPLICATION_COUNT = 5000
TRANSACTIONS_PER_APPLICANT = (8, 40)
START_DATE = datetime(2025, 1, 1)

EMPLOYMENT_STATUSES = ["employed", "self_employed", "gig_worker", "student", "unemployed"]
LOAN_PURPOSES = ["personal", "auto", "education", "debt_consolidation", "home_improvement"]
MERCHANT_CATEGORIES = [
    "groceries",
    "utilities",
    "transport",
    "dining",
    "healthcare",
    "rent",
    "education",
    "entertainment",
    "cash_withdrawal",
    "transfer",
]


def weighted_choice(items: list[str], weights: list[float]) -> str:
    return RNG.choices(items, weights=weights, k=1)[0]


def make_applicant_id(index: int) -> str:
    return f"APP-{10000 + index:05d}"


def make_customer_id(index: int) -> str:
    return f"CUST-{20000 + index:05d}"


def generate_applications() -> list[dict]:
    rows: list[dict] = []
    for i in range(APPLICATION_COUNT):
        applicant_id = make_applicant_id(i)
        customer_id = make_customer_id(i)
        age = RNG.randint(21, 68)
        employment = weighted_choice(
            EMPLOYMENT_STATUSES,
            [0.55, 0.18, 0.12, 0.08, 0.07],
        )
        monthly_income = max(
            800,
            int(RNG.gauss(4200 if employment != "unemployed" else 1200, 1400)),
        )
        requested_amount = RNG.choice([3000, 5000, 8000, 12000, 15000, 20000, 25000])
        tenure_months = RNG.randint(1, 84)
        existing_loans = RNG.randint(0, 4)
        credit_history_months = RNG.randint(0, 180)
        thin_file = 1 if credit_history_months < 12 else 0
        utility_on_time_pct = round(RNG.uniform(0.55, 1.0), 3)
        cash_flow_stability = round(RNG.uniform(0.2, 0.95), 3)
        inquiry_count_90d = RNG.randint(0, 8)
        debt_to_income = round(
            RNG.uniform(0.08, 0.72) + (existing_loans * 0.04),
            3,
        )
        device_trust_score = round(RNG.uniform(0.35, 0.99), 3)
        prior_default = 1 if RNG.random() < 0.08 else 0

        risk_signal = (
            0.30 * (1 - cash_flow_stability)
            + 0.22 * (inquiry_count_90d / 8)
            + 0.22 * debt_to_income
            + 0.16 * prior_default
            + 0.10 * (1 - utility_on_time_pct)
        )
        if thin_file:
            risk_signal += 0.05
        if employment in {"gig_worker", "unemployed"}:
            risk_signal += 0.04

        default_probability = min(0.95, max(0.03, risk_signal + RNG.uniform(-0.04, 0.04)))
        defaulted = 1 if RNG.random() < default_probability else 0
        risk_profile = default_probability

        applied_at = START_DATE + timedelta(days=RNG.randint(0, 300), hours=RNG.randint(0, 23))
        rows.append(
            {
                "application_id": applicant_id,
                "customer_id": customer_id,
                "applied_at": applied_at.strftime("%Y-%m-%d %H:%M:%S"),
                "age": age,
                "employment_status": employment,
                "monthly_income": monthly_income,
                "requested_loan_amount": requested_amount,
                "loan_purpose": weighted_choice(
                    LOAN_PURPOSES,
                    [0.35, 0.18, 0.12, 0.20, 0.15],
                ),
                "tenure_months": tenure_months,
                "existing_loans": existing_loans,
                "credit_history_months": credit_history_months,
                "thin_file": thin_file,
                "utility_on_time_pct": utility_on_time_pct,
                "cash_flow_stability_score": cash_flow_stability,
                "inquiry_count_90d": inquiry_count_90d,
                "debt_to_income_ratio": debt_to_income,
                "device_trust_score": device_trust_score,
                "prior_default_flag": prior_default,
                "region": weighted_choice(
                    ["north", "south", "east", "west", "central"],
                    [0.22, 0.18, 0.24, 0.20, 0.16],
                ),
                "risk_profile": round(risk_profile, 4),
                "defaulted": defaulted,
            }
        )
    return rows


def generate_transactions(applications: list[dict]) -> list[dict]:
    rows: list[dict] = []
    txn_counter = 1
    for app in applications:
        txn_count = RNG.randint(*TRANSACTIONS_PER_APPLICANT)
        base_date = datetime.strptime(app["applied_at"], "%Y-%m-%d %H:%M:%S")
        monthly_income = app["monthly_income"]
        risk_profile = app["risk_profile"]
        spend_multiplier = 0.8 + (risk_profile * 0.9)
        income_multiplier = max(0.45, 1.1 - (risk_profile * 0.8))
        for _ in range(txn_count):
            days_before = RNG.randint(1, 90)
            txn_at = base_date - timedelta(days=days_before, hours=RNG.randint(0, 23))
            category = weighted_choice(
                MERCHANT_CATEGORIES,
                [0.18, 0.12, 0.10, 0.08, 0.06, 0.12, 0.05, 0.07, 0.10, 0.12],
            )
            if category in {"rent", "utilities", "groceries"}:
                amount = round(RNG.uniform(25, min(1800, monthly_income * 0.45)) * spend_multiplier, 2)
            elif category == "cash_withdrawal":
                amount = round(RNG.uniform(40, min(900, monthly_income * 0.25)) * spend_multiplier, 2)
            else:
                amount = round(RNG.uniform(5, min(500, monthly_income * 0.15)) * spend_multiplier, 2)

            is_income = category == "transfer" and RNG.random() < 0.35
            if is_income:
                amount = round(RNG.uniform(monthly_income * 0.6, monthly_income * 1.1) * income_multiplier, 2)

            rows.append(
                {
                    "transaction_id": f"TXN-{txn_counter:07d}",
                    "application_id": app["application_id"],
                    "customer_id": app["customer_id"],
                    "transaction_at": txn_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "merchant_category": category,
                    "amount": amount,
                    "is_income": 1 if is_income else 0,
                    "channel": weighted_choice(["mobile", "web", "branch", "atm"], [0.55, 0.20, 0.10, 0.15]),
                    "is_international": 1 if RNG.random() < 0.04 else 0,
                }
            )
            txn_counter += 1
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_policy() -> None:
    policy = """# NovaBank Credit Policy (Demo)

Version: 2026.1
Audience: Retail lending underwriters

## 1. Purpose
This policy governs automated and manual credit decisions for personal loans up to USD 25,000.

## 2. Thin-file applicants
An applicant is thin-file when credit_history_months < 12.

Rules:
- If model default probability > 0.65, route to manual review.
- Require 2 additional bank statements when cash_flow_stability_score < 0.50.
- Utility payment on-time percentage below 0.80 requires income verification.

## 3. Automated decision tiers
- Approve: default probability <= 0.35 and debt_to_income_ratio <= 0.45
- Review: default probability between 0.36 and 0.65, or thin_file = 1 with probability <= 0.55
- Decline: default probability > 0.65, or prior_default_flag = 1 with probability > 0.40

## 4. Maximum exposure
- Maximum debt_to_income_ratio for approval: 0.45
- Maximum requested_loan_amount for gig_worker without co-signer: USD 10,000
- Maximum inquiry_count_90d for auto-approval: 3

## 5. Adverse action requirements
Decline notices must cite specific contributing factors such as:
- recent credit inquiries
- unstable cash inflow patterns
- high debt-to-income ratio
- prior default history

Generic reasons like "credit history" alone are not acceptable.

## 6. Fraud and device trust
- device_trust_score < 0.55 requires step-up authentication
- More than 2 international transactions in 30 days triggers fraud review

## 7. Model governance
- Champion model must be registered in Cloudera AI Registry
- Any model promotion requires validation AUC >= 0.72 on holdout thin-file segment
- Feature tables must be sourced from governed Iceberg gold tables only
"""
    (POLICY_DIR / "credit_policy.md").write_text(policy, encoding="utf-8")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    POLICY_DIR.mkdir(parents=True, exist_ok=True)

    applications = generate_applications()
    transactions = generate_transactions(applications)

    write_csv(DATA_DIR / "applications.csv", applications)
    write_csv(DATA_DIR / "transactions.csv", transactions)
    write_policy()

    thin_file_count = sum(row["thin_file"] for row in applications)
    default_rate = sum(row["defaulted"] for row in applications) / len(applications)

    print(f"Wrote {len(applications)} applications -> {DATA_DIR / 'applications.csv'}")
    print(f"Wrote {len(transactions)} transactions -> {DATA_DIR / 'transactions.csv'}")
    print(f"Wrote policy -> {POLICY_DIR / 'credit_policy.md'}")
    print(f"Thin-file applicants: {thin_file_count} ({thin_file_count / len(applications):.1%})")
    print(f"Observed default rate: {default_rate:.1%}")


if __name__ == "__main__":
    main()
