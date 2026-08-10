# 1-Day Workshop Agenda

**Title:** Intelligent Credit Decisioning with CDE + CAI  
**Duration:** 6.5 hours (09:00 – 17:00)  
**Audience:** Data engineers, data scientists, architects

## Schedule

| Time | Session | Owner | Format |
|------|---------|-------|--------|
| 09:00–09:30 | Welcome, use case, architecture | Facilitator | Presentation |
| 09:30–10:15 | Lab 0 + Lab 1: Ingest | Participants | Hands-on |
| 10:15–10:30 | Break | | |
| 10:30–11:30 | Lab 2: Features + facilitator CDE demo | Participants | Hands-on |
| 11:30–12:30 | Lab 3: Airflow DAG | Participants | Hands-on |
| 12:30–13:30 | Lunch | | |
| 13:30–14:45 | Lab 4: Train model (CAI) | Participants | Hands-on |
| 14:45–15:00 | Break | | |
| 15:00–15:45 | Lab 5: Deploy model | Participants | Hands-on |
| 15:45–16:30 | Lab 6: Batch scoring | Participants | Hands-on |
| 16:30–17:00 | Lab 7 + governance Q&A | Facilitator | Demo + discussion |

## End state (what customers leave with)

- Working Iceberg tables: `raw_applications`, `features`, `scores`
- Trained model in MLflow registry
- Deployed scoring API
- Airflow DAG they can re-trigger
- Understanding of CDE ↔ CAI integration pattern

## Facilitator pacing notes

- If behind at 11:00: skip Lab 0 for participants (pre-validated)
- If behind at 15:00: facilitator deploys model while participants finish Lab 4
- If ahead: run SHAP Lab 7 and MLOps discussion
