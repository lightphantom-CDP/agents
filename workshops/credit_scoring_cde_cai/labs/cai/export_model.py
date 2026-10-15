"""
Export best MLflow run model to /home/cdsw/model_files for deploy-from-code.

Run in CAI after Lab 4 training completes.
"""

import mlflow
from mlflow.tracking import MlflowClient

EXPERIMENT_NAME = "credit_default_prediction"
OUTPUT_PATH = "/home/cdsw/model_files"


def main():
    client = MlflowClient()
    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        raise ValueError(f"Experiment not found: {EXPERIMENT_NAME}")

    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=["metrics.auc DESC"],
        max_results=1,
    )
    if not runs:
        raise ValueError(f"No runs found in experiment {EXPERIMENT_NAME}")

    best = runs[0]
    run_id = best.info.run_id
    auc = best.data.metrics.get("auc", "n/a")
    print(f"Best run: {run_id} auc={auc}")

    model_uri = f"runs:/{run_id}/model"
    mlflow.sklearn.save_model(mlflow.sklearn.load_model(model_uri), OUTPUT_PATH)
    print(f"SUCCESS: saved model to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
