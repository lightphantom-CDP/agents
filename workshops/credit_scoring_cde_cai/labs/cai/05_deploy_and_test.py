"""
Lab 5 — Test deployed CAI model API (run in CAI Workbench or local terminal).

Update MODEL_URL and AUTH_TOKEN before running.
"""

import json
import os

import requests

MODEL_URL = os.environ.get("CAI_MODEL_URL", "https://changeme/model/credit-scoring-api/infer")
AUTH_TOKEN = os.environ.get("CAI_MODEL_TOKEN", "")

# Feature order must match training (see PARTICIPANT_GUIDE.md)
SAMPLE_APPLICANTS = [
    {
        "name": "low_risk",
        "features": [0.15, 42, 0.20, 0, 6, 1, 0, 0, 6000.0, 0],
    },
    {
        "name": "high_risk",
        "features": [0.95, 28, 0.85, 5, 15, 0, 2, 1, 2500.0, 1],
    },
]


def risk_band(probability: float) -> str:
    if probability < 0.10:
        return "A"
    if probability < 0.20:
        return "B"
    if probability < 0.35:
        return "C"
    return "D"


def score_applicant(features):
    headers = {"Content-Type": "application/json"}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"

    response = requests.post(
        MODEL_URL,
        headers=headers,
        json={"inputs": [features]},
        timeout=30,
    )
    response.raise_for_status()
    body = response.json()

    if isinstance(body, dict) and "predictions" in body:
        pred = body["predictions"][0]
    elif isinstance(body, list):
        pred = body[0]
    else:
        pred = body.get("outputs", [0.0])[0]

    prob = float(pred[0] if isinstance(pred, (list, tuple)) else pred)
    return prob, risk_band(prob)


def main():
    for applicant in SAMPLE_APPLICANTS:
        prob, band = score_applicant(applicant["features"])
        print(
            json.dumps(
                {
                    "profile": applicant["name"],
                    "probability_default": round(prob, 4),
                    "risk_band": band,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
