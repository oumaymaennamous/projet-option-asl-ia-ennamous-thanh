import os
import sys

import mlflow
from mlflow import MlflowClient

mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"))
usage = "Usage: smoke-test.py write | read <run_id>"

if sys.argv[1:2] == ["write"]:
    mlflow.set_experiment("j3-smoke")
    with mlflow.start_run(run_name="smoke-j3") as run:
        mlflow.log_param("check", "j3")
        mlflow.log_metric("value", 1.0)
        mlflow.log_text("MLflow J3 : artefact conserve", "smoke.txt")
    print("run_id      :", run.info.run_id)
    print("artifact_uri:", run.info.artifact_uri)
elif len(sys.argv) == 3 and sys.argv[1] == "read":
    client = MlflowClient()
    run = client.get_run(sys.argv[2])
    print("params      :", run.data.params)
    print("metrics     :", run.data.metrics)
    path = mlflow.artifacts.download_artifacts(run_id=sys.argv[2], artifact_path="smoke.txt")
    print("artefact    :", open(path, encoding="utf-8").read())
else:
    raise SystemExit(usage)