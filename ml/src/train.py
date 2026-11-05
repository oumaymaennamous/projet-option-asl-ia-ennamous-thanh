import argparse, subprocess, os
from pathlib import Path
import mlflow, mlflow.sklearn
import numpy as np
import pandas as pd
from mlflow.models import infer_signature
from sklearn.datasets import fetch_california_housing
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


TELCO_URL = (
    "https://raw.githubusercontent.com/IBM/"
    "telco-customer-churn-on-icp4d/master/data/Telco-Customer-Churn.csv"
)


# ---------------------------------------------------------------- utilities
def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:
        return "unknown"


# ---------------------------------------------------------------- datasets
def load_housing(seed: int, test_size: float):
    """California Housing — régression continue."""
    X, y = fetch_california_housing(return_X_y=True, as_frame=True)
    return train_test_split(X, y, test_size=test_size, random_state=seed)


def load_churn(seed: int, test_size: float):
    """Telco Customer Churn — classification binaire (Yes/No).

    Priorité fichier local ml/data/telco_churn.csv (si présent),
    sinon téléchargement depuis le miroir GitHub IBM (puis cache local).
    """
    local = Path("data/telco_churn.csv")
    if local.exists():
        df = pd.read_csv(local)
    else:
        print(f"[data] downloading Telco Churn from {TELCO_URL}")
        df = pd.read_csv(TELCO_URL)
        # Cache local pour éviter les téléchargements répétés
        local.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(local, index=False)
        print(f"[data] cached to {local} ({len(df)} rows)")

    # TotalCharges: chaîne avec espaces, à convertir et nettoyer
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    df = df.dropna(subset=["TotalCharges"]).reset_index(drop=True)

    y = (df["Churn"] == "Yes").astype(int)
    X = df.drop(columns=["customerID", "Churn"])
    X = pd.get_dummies(X, drop_first=True)

    # Cast numériques en float64 (évite warning infer_signature + schema enforcement)
    num_cols = X.select_dtypes(include=["int", "int64", "int32"]).columns
    X[num_cols] = X[num_cols].astype("float64")

    return train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y
    )

# ---------------------------------------------------------------- models
def build_model(dataset: str, name: str, seed: int):
    """Return an unfitted sklearn estimator or Pipeline."""
    if dataset == "housing":
        if name == "rf":
            return RandomForestRegressor(
                n_estimators=100, random_state=seed, n_jobs=-1
            )
        if name == "ridge":
            return Pipeline(
                [("scaler", StandardScaler()), ("model", Ridge(alpha=1.0))]
            )
    elif dataset == "churn":
        if name == "rf":
            return RandomForestClassifier(
                n_estimators=100,
                random_state=seed,
                n_jobs=-1,
                class_weight="balanced",
            )
        if name == "logreg":
            return Pipeline(
                [
                    ("scaler", StandardScaler()),
                    (
                        "model",
                        LogisticRegression(
                            max_iter=1000,
                            random_state=seed,
                            class_weight="balanced",
                        ),
                    ),
                ]
            )
    raise ValueError(
        f"model {name!r} incompatible with dataset {dataset!r}"
    )


# ---------------------------------------------------------------- metrics
def evaluate(dataset: str, model, Xte, yte) -> dict:
    """Return a dict of metrics for MLflow logging."""
    pred = model.predict(Xte)
    metrics = {}

    if dataset == "housing":
        metrics["rmse"] = float(mean_squared_error(yte, pred) ** 0.5)
        metrics["r2"] = float(r2_score(yte, pred))
    else:  # churn
        metrics["accuracy"] = float(accuracy_score(yte, pred))
        metrics["precision"] = float(
            precision_score(yte, pred, zero_division=0)
        )
        metrics["recall"] = float(recall_score(yte, pred, zero_division=0))
        metrics["f1"] = float(f1_score(yte, pred, zero_division=0))

        # ROC AUC + seuil de décision (V3)
        proba = model.predict_proba(Xte)[:, 1]
        metrics["roc_auc"] = float(roc_auc_score(yte, proba))
        for thr in (0.30, 0.50, 0.70):
            pred_thr = (proba >= thr).astype(int)
            key = f"f1_thr_{int(thr * 100)}"
            metrics[key] = float(f1_score(yte, pred_thr, zero_division=0))

    return metrics


# ---------------------------------------------------------------- main
def main():
    parser = argparse.ArgumentParser(
        description="MLflow baseline: Housing (regression) "
        "or Churn (classification)"
    )
    parser.add_argument(
        "--dataset",
        choices=["housing", "churn"],
        default="churn",
        help="housing (POC historique) ou churn (J3, V3)",
    )
    parser.add_argument(
        "--model",
        default="auto",
        help="auto | rf | ridge (housing) | logreg (churn)",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument(
        "--experiment",
        default=None,
        help="Override experiment name (default: p3-baseline for housing, "
        "p3-churn for churn)",
    )
    args = parser.parse_args()

    # Auto model
    if args.model == "auto":
        args.model = {"housing": "rf", "churn": "logreg"}[args.dataset]

    # Experiment name (keep p3-baseline for housing to preserve old runs)
    default_exp = "p3-baseline" if args.dataset == "housing" else "p3-churn"
    experiment = args.experiment or default_exp

    mlflow.set_tracking_uri(
        os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
    )
    mlflow.set_experiment(experiment)

    # Load data
    if args.dataset == "housing":
        Xtr, Xte, ytr, yte = load_housing(args.seed, args.test_size)
    else:
        Xtr, Xte, ytr, yte = load_churn(args.seed, args.test_size)

    # Train
    model = build_model(args.dataset, args.model, args.seed)
    model.fit(Xtr, ytr)

    # Signature: predict_proba for classifiers, predict for regressors
    if hasattr(model, "predict_proba"):
        sig_pred = model.predict_proba(Xtr)
    else:
        sig_pred = model.predict(Xtr)
    sig = infer_signature(Xtr, sig_pred)

    # Evaluate
    metrics = evaluate(args.dataset, model, Xte, yte)

    run_name = f"EXP-J3-{args.dataset}-{args.model}-seed{args.seed}"

    with mlflow.start_run(run_name=run_name):
        mlflow.log_params(
            {
                "dataset": args.dataset,
                "model": args.model,
                "seed": args.seed,
                "test_size": args.test_size,
                "n_features": Xtr.shape[1],
                "n_train": len(Xtr),
                "n_test": len(Xte),
            }
        )
        for k, v in metrics.items():
            mlflow.log_metric(k, v)

        mlflow.set_tag("git_commit", git_commit())
        mlflow.set_tag("pipeline_stage", "baseline")

        # Tree models benefit from skops; others ignore it
        log_kwargs = {
            "name": "model",
            "signature": sig,
            "input_example": Xtr.head(3),
        }
        if args.model == "rf":
            log_kwargs["skops_trusted_types"] = ["sklearn.tree._tree.Tree"]
        mlflow.sklearn.log_model(model, **log_kwargs)

        summary = " ".join(
            f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}"
            for k, v in metrics.items()
        )
        print(f"[run] {run_name} ({experiment})  {summary}")
        print(
            f"[ui]  {mlflow.get_tracking_uri()}/#/experiments/"
            f"{mlflow.get_experiment_by_name(experiment).experiment_id}"
        )


if __name__ == "__main__":
    main()