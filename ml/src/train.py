import argparse, subprocess, os
import mlflow, mlflow.sklearn
from sklearn.datasets import fetch_california_housing
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from mlflow.models import infer_signature

def git_commit():
    try: return subprocess.check_output(["git","rev-parse","HEAD"], text=True).strip()
    except: return "unknown"

p = argparse.ArgumentParser()
p.add_argument("--model", choices=["rf","ridge"], default="rf")
p.add_argument("--seed", type=int, default=42)
args = p.parse_args()

mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"))
mlflow.set_experiment("p3-baseline")

X, y = fetch_california_housing(return_X_y=True, as_frame=True)
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=args.seed)

m = (RandomForestRegressor(n_estimators=100, random_state=args.seed, n_jobs=-1)
     if args.model == "rf" else Ridge(alpha=1.0)).fit(Xtr, ytr)
pred = m.predict(Xte)
sig = infer_signature(Xtr, m.predict(Xtr))

with mlflow.start_run(run_name=f"EXP-J3-{args.model}-seed{args.seed}"):
    mlflow.log_params({"model": args.model, "seed": args.seed})
    mlflow.log_metric("rmse", mean_squared_error(yte, pred) ** 0.5)
    mlflow.log_metric("r2", r2_score(yte, pred))
    mlflow.set_tag("git_commit", git_commit())
    mlflow.sklearn.log_model(m, "model", signature=sig, input_example=Xtr.head(3))