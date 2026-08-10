# 2-Day Workshop Agenda

**Title:** Build Production Credit Scoring on Cloudera  
**Duration:** 2 × 6.5 hours

## Day 1 — Data engineering foundation (CDE)

| Time | Module | Labs |
|------|--------|------|
| 09:00–09:45 | Architecture + credit use case deep dive | Slides |
| 09:45–10:30 | Lab 0: Environment validation | Lab 0 |
| 10:30–10:45 | Break | |
| 10:45–12:00 | Lab 1–2: Ingest + feature engineering | Labs 1–2 |
| 12:00–13:00 | Lunch | |
| 13:00–14:30 | Lab 3: Airflow + data quality | Lab 3 |
| 14:30–14:45 | Break | |
| 14:45–16:00 | Advanced CDE: performance tuning, partitioning | Discussion |
| 16:00–17:00 | Customer data mapping exercise | Whiteboard |

**Day 1 deliverable:** Scheduled CDE pipeline producing `workshop_credit.features`

## Day 2 — AI/ML + production scoring (CAI)

| Time | Module | Labs |
|------|--------|------|
| 09:00–09:30 | ML lifecycle on CAI recap | Slides |
| 09:30–11:00 | Lab 4: Train + MLflow experiments | Lab 4 |
| 11:00–11:15 | Break | |
| 11:15–12:00 | Lab 5: Model registry + deployment | Lab 5 |
| 12:00–13:00 | Lunch | |
| 13:00–14:15 | Lab 6: CDE batch scoring integration | Lab 6 |
| 14:15–14:30 | Break | |
| 14:30–15:15 | Lab 7: Explainability + governance | Lab 7 |
| 15:15–16:00 | MLOps roadmap (monitoring, retrain) | Presentation |
| 16:00–17:00 | Capstone demo + PoC planning | All |

**Day 2 deliverable:** End-to-end scored portfolio + PoC proposal draft

## Day 2 capstone script (facilitator)

1. Trigger Airflow DAG live
2. Show features refresh
3. Show batch scores landing
4. Pull one high-risk applicant → SHAP reasons
5. Show MLflow lineage (snapshot ID, model version)
6. Open floor: "How would this map to your environment?"

## Optional homework between days

- Participants review their internal credit data dictionary
- Facilitator pre-trains a champion model as backup
