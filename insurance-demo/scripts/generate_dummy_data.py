#!/usr/bin/env python3
"""Generate synthetic medical insurance claim datasets for CDE + Cloudera AI demos."""

from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
POLICY_DIR = DATA_DIR / "policy"

RNG = random.Random(42)

MEMBER_COUNT = 2000
CLAIMS_PER_MEMBER_RANGE = (1, 4)
START_DATE = datetime(2024, 1, 1)

PLAN_TYPES = {
    "basic": {
        "annual_limit": 15000,
        "deductible": 2000,
        "waiting_days": 90,
        "pre_auth_threshold": 3000,
        "maternity": False,
        "dental": False,
        "mental_health": False,
        "experimental": False,
    },
    "standard": {
        "annual_limit": 50000,
        "deductible": 1000,
        "waiting_days": 30,
        "pre_auth_threshold": 8000,
        "maternity": True,
        "dental": False,
        "mental_health": True,
        "experimental": False,
    },
    "premium": {
        "annual_limit": 200000,
        "deductible": 500,
        "waiting_days": 0,
        "pre_auth_threshold": 25000,
        "maternity": True,
        "dental": True,
        "mental_health": True,
        "experimental": True,
    },
}

HOSPITALS = [
    ("HSP-001", "City General Hospital"),
    ("HSP-002", "Metro Medical Center"),
    ("HSP-003", "Sunrise Community Clinic"),
    ("HSP-004", "Pacific Specialty Hospital"),
    ("HSP-005", "Riverside Emergency Care"),
]

DIAGNOSES = [
    ("J06.9", "Acute upper respiratory infection", "respiratory", 0.15, False),
    ("I10", "Essential hypertension", "cardiovascular", 0.10, True),
    ("E11.9", "Type 2 diabetes mellitus", "endocrine", 0.12, True),
    ("S72.001A", "Fracture of femur", "trauma", 0.08, False),
    ("K35.80", "Acute appendicitis", "surgical", 0.06, False),
    ("O80", "Normal delivery", "maternity", 0.05, False),
    ("F32.1", "Major depressive disorder", "mental_health", 0.07, True),
    ("M54.5", "Low back pain", "musculoskeletal", 0.11, False),
    ("N18.3", "Chronic kidney disease stage 3", "renal", 0.04, True),
    ("C50.911", "Malignant neoplasm of breast", "oncology", 0.03, True),
    ("J18.9", "Pneumonia", "respiratory", 0.06, False),
    ("K21.9", "Gastro-esophageal reflux disease", "digestive", 0.05, True),
    ("G43.909", "Migraine", "neurology", 0.04, False),
    ("H66.90", "Otitis media", "ent", 0.04, False),
]

PROCEDURES = {
    "respiratory": [
        ("99213", "Office visit - established patient", 150, 1, False),
        ("71046", "Chest X-ray", 280, 1, False),
        ("94640", "Nebulizer treatment", 120, 2, False),
    ],
    "cardiovascular": [
        ("93000", "Electrocardiogram", 220, 1, False),
        ("99214", "Office visit - moderate complexity", 250, 1, False),
        ("93306", "Echocardiography", 1800, 1, True),
    ],
    "endocrine": [
        ("82947", "Glucose blood test", 45, 1, False),
        ("99213", "Diabetes follow-up visit", 180, 1, False),
        ("J1815", "Insulin injection", 95, 4, False),
    ],
    "trauma": [
        ("27506", "Femur fracture repair", 12000, 1, True),
        ("73721", "MRI lower extremity", 2200, 1, True),
        ("99223", "Initial hospital care - high severity", 650, 1, False),
    ],
    "surgical": [
        ("44970", "Laparoscopic appendectomy", 8500, 1, True),
        ("99223", "Initial hospital care - high severity", 650, 2, False),
        ("80053", "Comprehensive metabolic panel", 120, 1, False),
    ],
    "maternity": [
        ("59400", "Routine obstetric care", 6500, 1, True),
        ("59510", "Cesarean delivery", 14000, 1, True),
        ("76805", "Obstetric ultrasound", 450, 2, False),
    ],
    "mental_health": [
        ("90834", "Psychotherapy 45 minutes", 180, 4, False),
        ("99213", "Psychiatric follow-up", 200, 2, False),
    ],
    "musculoskeletal": [
        ("72148", "MRI lumbar spine", 2100, 1, True),
        ("97110", "Therapeutic exercises", 85, 8, False),
        ("20610", "Joint injection", 350, 1, False),
    ],
    "renal": [
        ("90935", "Hemodialysis procedure", 450, 12, True),
        ("80069", "Renal function panel", 95, 4, False),
    ],
    "oncology": [
        ("96413", "Chemotherapy administration", 3200, 6, True),
        ("77385", "Radiation treatment", 8500, 8, True),
        ("88305", "Surgical pathology", 420, 2, False),
    ],
    "digestive": [
        ("43239", "Upper GI endoscopy", 2800, 1, True),
        ("99213", "GI follow-up visit", 175, 1, False),
    ],
    "neurology": [
        ("70553", "MRI brain", 2400, 1, True),
        ("99214", "Neurology consultation", 320, 1, False),
    ],
    "ent": [
        ("69210", "Ear wax removal", 95, 1, False),
        ("92567", "Tympanometry", 75, 1, False),
    ],
}

BILL_CATEGORIES = [
    ("room", 0.35),
    ("lab", 0.12),
    ("pharmacy", 0.18),
    ("surgery", 0.20),
    ("imaging", 0.10),
    ("consultation", 0.05),
]

FIRST_NAMES = [
    "Aisha", "Ben", "Carlos", "Diana", "Ethan", "Fatima", "Grace", "Hassan",
    "Ivy", "James", "Keiko", "Liam", "Maya", "Noah", "Olivia", "Priya",
    "Quinn", "Ravi", "Sofia", "Thomas", "Uma", "Victor", "Wendy", "Xavier",
    "Yuki", "Zara",
]
LAST_NAMES = [
    "Chen", "Patel", "Nguyen", "Garcia", "Kim", "Singh", "Brown", "Ali",
    "Martinez", "Johnson", "Wong", "Anderson", "Lee", "Taylor", "Hassan",
    "Wilson", "Okonkwo", "Santos", "Murphy", "Khan",
]
REGIONS = ["north", "south", "east", "west", "central"]


def weighted_choice(items: list, weights: list[float]):
    return RNG.choices(items, weights=weights, k=1)[0]


def make_member_id(index: int) -> str:
    return f"MEM-{30000 + index:05d}"


def make_policy_id(index: int) -> str:
    return f"POL-{40000 + index:05d}"


def make_claim_id(counter: int) -> str:
    return f"CLM-{50000 + counter:05d}"


def random_date_between(start: datetime, end: datetime) -> datetime:
    delta_days = (end - start).days
    if delta_days <= 0:
        return start
    return start + timedelta(days=RNG.randint(0, delta_days), hours=RNG.randint(0, 23))


def generate_members() -> list[dict]:
    rows: list[dict] = []
    for i in range(MEMBER_COUNT):
        member_id = make_member_id(i)
        age = RNG.randint(18, 78)
        dob = datetime(2026 - age, RNG.randint(1, 12), RNG.randint(1, 28))
        rows.append(
            {
                "member_id": member_id,
                "full_name": f"{RNG.choice(FIRST_NAMES)} {RNG.choice(LAST_NAMES)}",
                "date_of_birth": dob.strftime("%Y-%m-%d"),
                "age": age,
                "gender": weighted_choice(["female", "male", "other"], [0.51, 0.47, 0.02]),
                "region": weighted_choice(REGIONS, [0.22, 0.18, 0.24, 0.20, 0.16]),
                "smoker_flag": 1 if RNG.random() < 0.14 else 0,
                "bmi_category": weighted_choice(
                    ["underweight", "normal", "overweight", "obese"],
                    [0.04, 0.38, 0.36, 0.22],
                ),
            }
        )
    return rows


def generate_policies(members: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for i, member in enumerate(members):
        plan_type = weighted_choice(
            list(PLAN_TYPES.keys()),
            [0.35, 0.45, 0.20],
        )
        plan = PLAN_TYPES[plan_type]
        coverage_start = START_DATE - timedelta(days=RNG.randint(30, 900))
        deductible_used = round(RNG.uniform(0, plan["deductible"] * 0.85), 2)
        rows.append(
            {
                "policy_id": make_policy_id(i),
                "member_id": member["member_id"],
                "plan_type": plan_type,
                "annual_coverage_limit": plan["annual_limit"],
                "annual_deductible": plan["deductible"],
                "deductible_used_ytd": deductible_used,
                "waiting_period_days": plan["waiting_days"],
                "coverage_start_date": coverage_start.strftime("%Y-%m-%d"),
                "coverage_end_date": (coverage_start + timedelta(days=365)).strftime("%Y-%m-%d"),
                "pre_auth_threshold": plan["pre_auth_threshold"],
                "maternity_covered": 1 if plan["maternity"] else 0,
                "dental_covered": 1 if plan["dental"] else 0,
                "mental_health_covered": 1 if plan["mental_health"] else 0,
                "experimental_treatment_covered": 1 if plan["experimental"] else 0,
                "policy_status": weighted_choice(["active", "active", "active", "lapsed"], [0.7, 0.15, 0.10, 0.05]),
            }
        )
    return rows


def generate_medical_history(members: list[dict], policies: list[dict]) -> list[dict]:
    rows: list[dict] = []
    policy_by_member = {p["member_id"]: p for p in policies}
    chronic_diagnoses = [d for d in DIAGNOSES if d[4]]

    for member in members:
        policy = policy_by_member[member["member_id"]]
        coverage_start = datetime.strptime(policy["coverage_start_date"], "%Y-%m-%d")
        history_count = RNG.randint(0, 3)
        chosen = RNG.sample(chronic_diagnoses, k=min(history_count, len(chronic_diagnoses)))

        for code, name, category, _, is_chronic in chosen:
            diagnosed_date = coverage_start - timedelta(days=RNG.randint(180, 2500))
            disclosed = 1 if RNG.random() < 0.82 else 0
            rows.append(
                {
                    "history_id": f"HIS-{len(rows) + 1:06d}",
                    "member_id": member["member_id"],
                    "condition_code": code,
                    "condition_name": name,
                    "diagnosed_date": diagnosed_date.strftime("%Y-%m-%d"),
                    "is_chronic": 1 if is_chronic else 0,
                    "disclosed_on_enrollment": disclosed,
                    "is_pre_existing": 1 if diagnosed_date < coverage_start else 0,
                }
            )
    return rows


def pick_diagnosis_for_claim(member_history: list[dict], plan: dict) -> tuple:
    undisclosed_pre_existing = [
        h for h in member_history if h["is_pre_existing"] and not h["disclosed_on_enrollment"]
    ]
    if undisclosed_pre_existing and RNG.random() < 0.35:
        history_row = RNG.choice(undisclosed_pre_existing)
        for diag in DIAGNOSES:
            if diag[0] == history_row["condition_code"]:
                return diag

    eligible = list(DIAGNOSES)
    if not plan["maternity_covered"]:
        eligible = [d for d in eligible if d[2] != "maternity"]
    if not plan["mental_health_covered"]:
        eligible = [d for d in eligible if d[2] != "mental_health"]
    weights = [d[3] for d in eligible]
    return weighted_choice(eligible, weights)


def compute_claim_outcome(
    *,
    total_billed: float,
    plan: dict,
    policy: dict,
    diagnosis: tuple,
    admission_type: str,
    has_prior_auth: bool,
    has_experimental: bool,
    days_since_coverage: int,
    undisclosed_pre_existing_match: bool,
    prior_claims_paid_ytd: float,
) -> tuple[str, float, list[str]]:
    reasons: list[str] = []
    score = 0.72

    remaining_limit = plan["annual_limit"] - prior_claims_paid_ytd
    if policy["policy_status"] != "active":
        return "rejected", 0.0, ["policy_not_active"]

    if days_since_coverage < plan["waiting_days"]:
        score -= 0.55
        reasons.append("waiting_period_not_met")

    if undisclosed_pre_existing_match:
        score -= 0.45
        reasons.append("undisclosed_pre_existing_condition")

    category = diagnosis[2]
    if category == "maternity" and not plan["maternity"]:
        score -= 0.50
        reasons.append("maternity_not_covered")
    if category == "mental_health" and not plan["mental_health"]:
        score -= 0.40
        reasons.append("mental_health_not_covered")

    if has_experimental and not plan["experimental"]:
        score -= 0.35
        reasons.append("experimental_treatment_excluded")

    if total_billed > plan["pre_auth_threshold"] and not has_prior_auth:
        score -= 0.30
        reasons.append("missing_prior_authorization")

    if total_billed > remaining_limit:
        score -= 0.25
        reasons.append("exceeds_annual_limit")

    if admission_type == "emergency":
        score += 0.12
    elif admission_type == "scheduled" and total_billed > 10000:
        score -= 0.08

    score += RNG.uniform(-0.08, 0.08)
    score = max(0.0, min(1.0, score))

    if score >= 0.72:
        outcome = "approved"
        approved_amount = round(total_billed * RNG.uniform(0.85, 1.0), 2)
    elif score >= 0.50:
        outcome = "partial_approval"
        approved_amount = round(total_billed * RNG.uniform(0.40, 0.75), 2)
        reasons.append("partial_coverage_applied")
    elif score >= 0.35:
        outcome = "manual_review"
        approved_amount = 0.0
        reasons.append("requires_clinical_review")
    else:
        outcome = "rejected"
        approved_amount = 0.0
        if not reasons:
            reasons.append("not_medically_necessary")

    approved_amount = min(approved_amount, remaining_limit)
    return outcome, approved_amount, reasons


def generate_claims(
    members: list[dict],
    policies: list[dict],
    medical_history: list[dict],
) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    policy_by_member = {p["member_id"]: p for p in policies}
    history_by_member: dict[str, list[dict]] = {}
    for row in medical_history:
        history_by_member.setdefault(row["member_id"], []).append(row)

    claims: list[dict] = []
    diagnoses_rows: list[dict] = []
    procedures_rows: list[dict] = []
    bills_rows: list[dict] = []

    claim_counter = 0
    bill_counter = 0
    paid_ytd_by_policy: dict[str, float] = {}

    for member in members:
        policy = policy_by_member[member["member_id"]]
        plan = PLAN_TYPES[policy["plan_type"]]
        member_history = history_by_member.get(member["member_id"], [])
        claim_count = RNG.randint(*CLAIMS_PER_MEMBER_RANGE)

        for _ in range(claim_count):
            claim_counter += 1
            claim_id = make_claim_id(claim_counter)
            hospital_id, hospital_name = RNG.choice(HOSPITALS)
            admission_type = weighted_choice(
                ["emergency", "scheduled", "outpatient"],
                [0.22, 0.28, 0.50],
            )

            coverage_start = datetime.strptime(policy["coverage_start_date"], "%Y-%m-%d")
            service_date = random_date_between(coverage_start, START_DATE + timedelta(days=300))
            days_since_coverage = (service_date - coverage_start).days

            diagnosis = pick_diagnosis_for_claim(member_history, policy)
            undisclosed_match = any(
                h["condition_code"] == diagnosis[0]
                and h["is_pre_existing"]
                and not h["disclosed_on_enrollment"]
                for h in member_history
            )

            proc_options = PROCEDURES.get(diagnosis[2], PROCEDURES["respiratory"])
            selected_procedures = RNG.sample(
                proc_options,
                k=RNG.randint(1, min(3, len(proc_options))),
            )

            has_prior_auth = RNG.random() < 0.55
            has_experimental = RNG.random() < 0.06

            procedure_total = 0.0
            for cpt_code, desc, unit_price, qty, requires_pre_auth in selected_procedures:
                line_total = round(unit_price * qty * RNG.uniform(0.95, 1.15), 2)
                procedure_total += line_total
                procedures_rows.append(
                    {
                        "claim_id": claim_id,
                        "procedure_code": cpt_code,
                        "procedure_description": desc,
                        "quantity": qty,
                        "unit_price": unit_price,
                        "line_total": line_total,
                        "requires_prior_auth": 1 if requires_pre_auth else 0,
                    }
                )

            room_nights = 0
            if admission_type in {"emergency", "scheduled"}:
                room_nights = RNG.randint(1, 7)
                procedure_total += room_nights * RNG.uniform(800, 2200)

            total_billed = round(procedure_total * RNG.uniform(1.0, 1.25), 2)
            prior_paid = paid_ytd_by_policy.get(policy["policy_id"], 0.0)

            outcome, approved_amount, reasons = compute_claim_outcome(
                total_billed=total_billed,
                plan=plan,
                policy=policy,
                diagnosis=diagnosis,
                admission_type=admission_type,
                has_prior_auth=has_prior_auth,
                has_experimental=has_experimental,
                days_since_coverage=days_since_coverage,
                undisclosed_pre_existing_match=undisclosed_match,
                prior_claims_paid_ytd=prior_paid,
            )

            if outcome in {"approved", "partial_approval"}:
                paid_ytd_by_policy[policy["policy_id"]] = prior_paid + approved_amount

            discharge_date = service_date + timedelta(days=room_nights)
            submitted_at = discharge_date + timedelta(hours=RNG.randint(4, 72))

            claims.append(
                {
                    "claim_id": claim_id,
                    "member_id": member["member_id"],
                    "policy_id": policy["policy_id"],
                    "hospital_id": hospital_id,
                    "hospital_name": hospital_name,
                    "admission_type": admission_type,
                    "admission_date": service_date.strftime("%Y-%m-%d"),
                    "discharge_date": discharge_date.strftime("%Y-%m-%d"),
                    "length_of_stay_days": room_nights,
                    "total_billed_amount": total_billed,
                    "submitted_at": submitted_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "prior_auth_number": f"PA-{RNG.randint(100000, 999999)}" if has_prior_auth else "",
                    "has_experimental_treatment": 1 if has_experimental else 0,
                    "attending_physician": f"Dr. {RNG.choice(LAST_NAMES)}",
                    "claim_outcome": outcome,
                    "approved_amount": approved_amount,
                    "denial_reasons": "|".join(reasons) if reasons else "",
                    "days_since_coverage_start": days_since_coverage,
                    "undisclosed_pre_existing_flag": 1 if undisclosed_match else 0,
                }
            )

            diagnoses_rows.append(
                {
                    "claim_id": claim_id,
                    "icd10_code": diagnosis[0],
                    "diagnosis_description": diagnosis[1],
                    "diagnosis_category": diagnosis[2],
                    "is_primary": 1,
                    "is_chronic_related": 1 if diagnosis[4] else 0,
                }
            )

            remaining = total_billed
            for category, weight in BILL_CATEGORIES:
                if remaining <= 0:
                    break
                amount = round(total_billed * weight * RNG.uniform(0.7, 1.3), 2)
                amount = min(amount, remaining)
                remaining -= amount
                bill_counter += 1
                bills_rows.append(
                    {
                        "bill_line_id": f"BIL-{bill_counter:07d}",
                        "claim_id": claim_id,
                        "line_category": category,
                        "description": f"{category.title()} charges",
                        "amount": amount,
                        "is_experimental": 1 if has_experimental and category == "surgery" and RNG.random() < 0.5 else 0,
                    }
                )

    return claims, diagnoses_rows, procedures_rows, bills_rows


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_policy() -> None:
    policy = """# MediShield Hospital Claims Policy (Demo)

Version: 2026.1
Audience: Medical claims review and AI agent reviewers

## 1. Purpose
This policy governs automated and manual decisions for inpatient, outpatient, and emergency hospital claims.

## 2. Covered services by plan

### Basic plan
- Annual limit: USD 15,000
- Waiting period: 90 days from coverage start
- Maternity, dental, mental health, and experimental treatments are excluded
- Prior authorization required for procedures over USD 3,000

### Standard plan
- Annual limit: USD 50,000
- Waiting period: 30 days
- Maternity and mental health covered; dental and experimental excluded
- Prior authorization required over USD 8,000

### Premium plan
- Annual limit: USD 200,000
- No waiting period
- Full coverage including maternity, dental, mental health, and approved experimental therapies
- Prior authorization required over USD 25,000

## 3. Automatic approval criteria
Approve when ALL of the following are true:
- Policy status is active
- Waiting period has elapsed
- Diagnosis and procedures are covered under the member plan
- Prior authorization is on file when billed amount exceeds plan threshold
- Total claim is within remaining annual limit
- No undisclosed pre-existing condition matches the primary diagnosis

## 4. Automatic rejection criteria
Reject when ANY of the following apply:
- Policy is lapsed or inactive
- Service date falls inside the waiting period
- Primary diagnosis relates to an undisclosed pre-existing condition
- Experimental treatment on Basic or Standard plans
- Maternity claim on a plan without maternity coverage
- Mental health claim on Basic plan

## 5. Manual review triggers
Route to clinical review when:
- Claim amount is between 60% and 90% of remaining annual limit
- Multiple high-cost procedures on the same admission
- Conflicting diagnosis and procedure codes
- Readmission within 7 days for the same diagnosis category

## 6. Partial approval rules
- Apply partial approval when medically necessary services are mixed with excluded line items
- Document each excluded line item in the denial reasons
- Member pays deductible before insurer share is calculated

## 7. Emergency admission override
Emergency admissions may bypass prior authorization requirements, but:
- Documentation must confirm emergency presentation
- Experimental treatments remain excluded unless Premium plan
- Annual limit still applies

## 8. Claim review transparency
Every decision must cite specific policy sections and clinical factors.
Generic denials such as "not covered" without diagnosis or policy reference are not acceptable.

## 9. Model and agent governance
- Champion claim review model must be registered in Cloudera AI Registry
- Feature tables must be sourced from governed Iceberg gold tables only
- Agent decisions must include: outcome, approved amount, policy citations, and top risk factors
"""
    (POLICY_DIR / "coverage_policy.md").write_text(policy, encoding="utf-8")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    POLICY_DIR.mkdir(parents=True, exist_ok=True)

    members = generate_members()
    policies = generate_policies(members)
    medical_history = generate_medical_history(members, policies)
    claims, diagnoses, procedures, bills = generate_claims(members, policies, medical_history)

    write_csv(DATA_DIR / "members.csv", members)
    write_csv(DATA_DIR / "policies.csv", policies)
    write_csv(DATA_DIR / "medical_history.csv", medical_history)
    write_csv(DATA_DIR / "claims.csv", claims)
    write_csv(DATA_DIR / "claim_diagnoses.csv", diagnoses)
    write_csv(DATA_DIR / "claim_procedures.csv", procedures)
    write_csv(DATA_DIR / "hospital_bills.csv", bills)
    write_policy()

    outcome_counts: dict[str, int] = {}
    for claim in claims:
        outcome_counts[claim["claim_outcome"]] = outcome_counts.get(claim["claim_outcome"], 0) + 1

    print(f"Wrote {len(members)} members -> {DATA_DIR / 'members.csv'}")
    print(f"Wrote {len(policies)} policies -> {DATA_DIR / 'policies.csv'}")
    print(f"Wrote {len(medical_history)} history rows -> {DATA_DIR / 'medical_history.csv'}")
    print(f"Wrote {len(claims)} claims -> {DATA_DIR / 'claims.csv'}")
    print(f"Wrote {len(diagnoses)} diagnoses -> {DATA_DIR / 'claim_diagnoses.csv'}")
    print(f"Wrote {len(procedures)} procedures -> {DATA_DIR / 'claim_procedures.csv'}")
    print(f"Wrote {len(bills)} bill lines -> {DATA_DIR / 'hospital_bills.csv'}")
    print(f"Wrote policy -> {POLICY_DIR / 'coverage_policy.md'}")
    print("\nClaim outcomes:")
    for outcome, count in sorted(outcome_counts.items()):
        print(f"  {outcome}: {count} ({count / len(claims):.1%})")


if __name__ == "__main__":
    main()
