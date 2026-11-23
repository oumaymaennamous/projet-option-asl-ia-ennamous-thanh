import argparse
import hashlib
import json
import os
import statistics
import subprocess
from pathlib import Path

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from mlflow import MlflowClient
from mlflow.models import infer_signature
from sklearn.compose import ColumnTransformer
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
from sklearn.preprocessing import OneHotEncoder, StandardScaler

TELCO_URL = (
    "https://raw.githubusercontent.com/IBM/"
    "telco-customer-churn-on-icp4d/master/data/Telco-Customer-Churn.csv"
)
TELCO_LICENSE = "IBM Sample Data / Apache-2.0 (miroir GitHub IBM icp4d)"
NUM_COLS = ["tenure", "MonthlyCharges", "TotalCharges"]
CAT_COLS = [
    "gender",
    "SeniorCitizen",
    "Partner",
    "Dependents",
    "PhoneService",
    "MultipleLines",
    "InternetService",
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
    "Contract",
    "PaperlessBilling",
    "PaymentMethod",
]
TRUSTED_TYPES = [
    "sklearn.compose._column_transformer._RemainderColsList",
    "sklearn.tree._tree.Tree",
]


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:
        return "unknown"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- datasets
def load_housing(seed: int, test_size: float):
    """California Housing — régression continue (POC historique)."""
    X, y = fetch_california_housing(return_X_y=True, as_frame=True)
    return train_test_split(X, y, test_size=test_size, random_state=seed)


def load_churn_raw() -> tuple[pd.DataFrame, pd.Series, dict]:
    """Charge et nettoie Telco Customer Churn sans encodage préalable (R10/R20)."""
    local = Path("data/telco_churn.csv")
    if not local.exists():
        print(f"[data] downloading Telco Churn from {TELCO_URL}")
        df_dl = pd.read_csv(TELCO_URL)
        local.parent.mkdir(parents=True, exist_ok=True)
        df_dl.to_csv(local, index=False)
        print(f"[data] cached to {local} ({len(df_dl)} rows)")

    file_hash = sha256_file(local)
    df = pd.read_csv(local)
    raw_rows = len(df)

    # TotalCharges : espaces vides -> NaN -> suppression
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    df = df.dropna(subset=["TotalCharges"]).reset_index(drop=True)

    # Normaliser les types bruts pour éviter les écarts de schéma (int vs float/str)
    for col in NUM_COLS:
        df[col] = df[col].astype("float64")
    df["SeniorCitizen"] = df["SeniorCitizen"].astype(str)
    for col in CAT_COLS:
        df[col] = df[col].astype(str)

    y = (df["Churn"] == "Yes").astype(int)
    X = df[NUM_COLS + CAT_COLS].copy()

    meta = {
        "dataset_source": TELCO_URL,
        "dataset_license": TELCO_LICENSE,
        "dataset_sha256": file_hash,
        "dataset_raw_rows": raw_rows,
        "dataset_clean_rows": len(df),
    }
    return X, y, meta


def split_churn_60_20_20(
    X: pd.DataFrame, y: pd.Series, split_seed: int = 42
):
    """Découpage stratifié 60% train / 20% validation / 20% test (R9)."""
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=0.20, random_state=split_seed, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=0.25, random_state=split_seed, stratify=y_temp
    )
    return X_train, X_val, X_test, y_train, y_val, y_test


# ---------------------------------------------------------------- models
def build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUM_COLS),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CAT_COLS,
            ),
        ],
        remainder="drop",
    )


def build_model(dataset: str, name: str, seed: int):
    """Construit une Pipeline complète intégrant le prétraitement (R10)."""
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
        pre = build_preprocessor()
        if name == "rf":
            clf = RandomForestClassifier(
                n_estimators=200,
                max_depth=10,
                min_samples_leaf=5,
                random_state=seed,
                n_jobs=-1,
                class_weight="balanced",
            )
            return Pipeline([("preprocessor", pre), ("model", clf)])
        if name == "logreg":
            clf = LogisticRegression(
                max_iter=1000,
                random_state=seed,
                class_weight="balanced",
            )
            return Pipeline([("preprocessor", pre), ("model", clf)])
    raise ValueError(f"model {name!r} incompatible with dataset {dataset!r}")


# ---------------------------------------------------------------- metrics
def evaluate_churn(model, X_eval: pd.DataFrame, y_eval: pd.Series, prefix: str) -> dict:
    """Calcule les métriques de classification avec préfixe (val_ ou test_)."""
    pred = model.predict(X_eval)
    proba = model.predict_proba(X_eval)[:, 1]
    metrics = {
        f"{prefix}_accuracy": float(accuracy_score(y_eval, pred)),
        f"{prefix}_precision": float(precision_score(y_eval, pred, zero_division=0)),
        f"{prefix}_recall": float(recall_score(y_eval, pred, zero_division=0)),
        f"{prefix}_f1": float(f1_score(y_eval, pred, zero_division=0)),
        f"{prefix}_roc_auc": float(roc_auc_score(y_eval, proba)),
    }
    for thr in (0.30, 0.50, 0.70):
        pred_thr = (proba >= thr).astype(int)
        metrics[f"{prefix}_f1_thr_{int(thr * 100)}"] = float(
            f1_score(y_eval, pred_thr, zero_division=0)
        )
    return metrics


# ---------------------------------------------------------------- housing (POC)
def run_housing(args):
    mlflow.set_experiment(args.experiment or "p3-baseline")
    Xtr, Xte, ytr, yte = load_housing(args.seed, 0.2)
    model = build_model("housing", args.model, args.seed)
    model.fit(Xtr, ytr)
    pred = model.predict(Xte)
    metrics = {
        "rmse": float(mean_squared_error(yte, pred) ** 0.5),
        "r2": float(r2_score(yte, pred)),
    }
    sig = infer_signature(Xtr, model.predict(Xtr))
    run_name = f"EXP-J3-housing-{args.model}-seed{args.seed}"
    with mlflow.start_run(run_name=run_name):
        mlflow.log_params({"dataset": "housing", "model": args.model, "seed": args.seed})
        for k, v in metrics.items():
            mlflow.log_metric(k, v)
        log_kwargs = {"name": "model", "signature": sig, "input_example": Xtr.head(3)}
        if args.model == "rf":
            log_kwargs["skops_trusted_types"] = TRUSTED_TYPES
        mlflow.sklearn.log_model(model, **log_kwargs)
        print(f"[run] {run_name}  {metrics}")


# ---------------------------------------------------------------- churn J3
def run_churn_campaign(args):
    experiment_name = args.experiment or "p3-churn"
    mlflow.set_experiment(experiment_name)
    client = MlflowClient()

    X, y, meta = load_churn_raw()
    X_train, X_val, X_test, y_train, y_val, y_test = split_churn_60_20_20(
        X, y, split_seed=args.split_seed
    )

    models_to_run = ["logreg", "rf"] if args.model == "all" else [args.model]
    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
    if len(seeds) < 3 and args.promote:
        raise ValueError("Au moins 3 graines sont requises pour la sélection J3.")

    results_by_model: dict[str, list[dict]] = {m: [] for m in models_to_run}
    commit = git_commit()

    for model_name in models_to_run:
        for seed in seeds:
            pipe = build_model("churn", model_name, seed)
            pipe.fit(X_train, y_train)

            val_metrics = evaluate_churn(pipe, X_val, y_val, prefix="val")
            sig = infer_signature(X_train, pipe.predict_proba(X_train))
            run_name = f"EXP-J3-churn-{model_name}-seed{seed}"

            with mlflow.start_run(run_name=run_name) as run:
                mlflow.log_params(
                    {
                        "dataset": "churn",
                        "model": model_name,
                        "seed": seed,
                        "split_seed": args.split_seed,
                        "split_ratio": "60/20/20",
                        "n_train": len(X_train),
                        "n_val": len(X_val),
                        "n_test": len(X_test),
                        "n_raw_features": X_train.shape[1],
                        **meta,
                    }
                )
                for k, v in val_metrics.items():
                    mlflow.log_metric(k, v)

                mlflow.set_tag("git_commit", commit)
                mlflow.set_tag("pipeline_stage", "j3-validation")
                mlflow.set_tag("preprocessing", "ColumnTransformer_in_Pipeline")

                log_kwargs = {
                    "name": "model",
                    "signature": sig,
                    "input_example": X_train.head(3),
                    "skops_trusted_types": TRUSTED_TYPES,
                }

                mlflow.sklearn.log_model(pipe, **log_kwargs)

                results_by_model[model_name].append(
                    {
                        "run_id": run.info.run_id,
                        "run_name": run_name,
                        "seed": seed,
                        "model_name": model_name,
                        "pipeline": pipe,
                        **val_metrics,
                    }
                )
                print(
                    f"[val] {run_name}  val_f1={val_metrics['val_f1']:.4f} "
                    f"val_recall={val_metrics['val_recall']:.4f} "
                    f"val_roc_auc={val_metrics['val_roc_auc']:.4f}"
                )

    print("\n=== Synthèse sur validation (médiane et dispersion IQR) ===")
    summary_stats = {}
    for model_name, runs in results_by_model.items():
        f1_vals = [r["val_f1"] for r in runs]
        rec_vals = [r["val_recall"] for r in runs]
        med_f1 = statistics.median(f1_vals)
        iqr_f1 = (
            float(np.percentile(f1_vals, 75) - np.percentile(f1_vals, 25))
            if len(f1_vals) > 1
            else 0.0
        )
        med_rec = statistics.median(rec_vals)
        summary_stats[model_name] = {
            "median_val_f1": med_f1,
            "iqr_val_f1": iqr_f1,
            "median_val_recall": med_rec,
            "all_val_f1": f1_vals,
        }
        print(
            f"  {model_name:6s} | médiane val_f1 = {med_f1:.4f} "
            f"(IQR = {iqr_f1:.4f}, min={min(f1_vals):.4f}, max={max(f1_vals):.4f}) "
            f"| médiane val_recall = {med_rec:.4f}"
        )

    if not args.promote:
        return

    # Sélection de la famille gagnante sur la médiane de val_f1 uniquement (R9)
    best_family = max(
        summary_stats.keys(), key=lambda m: summary_stats[m]["median_val_f1"]
    )
    family_runs = sorted(results_by_model[best_family], key=lambda r: r["val_f1"])
    # Choisir le run médian de la famille retenue
    champion_run = family_runs[len(family_runs) // 2]

    # Évaluation finale UNIQUE sur le jeu de test (R9)
    test_metrics = evaluate_churn(
        champion_run["pipeline"], X_test, y_test, prefix="test"
    )
    with mlflow.start_run(run_id=champion_run["run_id"]):
        for k, v in test_metrics.items():
            mlflow.log_metric(k, v)
        mlflow.set_tag("selected_champion", "true")

    # Enregistrement dans le Model Registry + alias champion
    reg_name = args.registered_model_name
    model_uri = f"runs:/{champion_run['run_id']}/model"
    mv = mlflow.register_model(model_uri=model_uri, name=reg_name)

    reason = (
        f"Promu champion J3 : famille '{best_family}' sélectionnée sur validation "
        f"(médiane val_f1={summary_stats[best_family]['median_val_f1']:.4f}, "
        f"IQR={summary_stats[best_family]['iqr_val_f1']:.4f} sur graines {seeds}). "
        f"Run représentatif : {champion_run['run_name']} "
        f"(val_f1={champion_run['val_f1']:.4f}, val_recall={champion_run['val_recall']:.4f}, "
        f"val_f1_thr_30={champion_run['val_f1_thr_30']:.4f}, "
        f"val_f1_thr_50={champion_run['val_f1_thr_50']:.4f}, "
        f"val_f1_thr_70={champion_run['val_f1_thr_70']:.4f}). "
        f"Évaluation unique sur test : test_f1={test_metrics['test_f1']:.4f}, "
        f"test_recall={test_metrics['test_recall']:.4f}, "
        f"test_roc_auc={test_metrics['test_roc_auc']:.4f}."
    )

    client.set_registered_model_alias(
        name=reg_name, alias="champion", version=mv.version
    )
    client.update_model_version(
        name=reg_name, version=mv.version, description=reason
    )
    client.set_model_version_tag(
        name=reg_name, version=mv.version, key="val_f1", value=f"{champion_run['val_f1']:.4f}"
    )
    client.set_model_version_tag(
        name=reg_name, version=mv.version, key="test_f1", value=f"{test_metrics['test_f1']:.4f}"
    )

    # Sauvegarde d'un échantillon de référence local (non versionné) pour --verify-reload
    ref_dir = Path("data")
    ref_dir.mkdir(parents=True, exist_ok=True)
    X_sample = X_test.head(20).copy()
    proba_ref = champion_run["pipeline"].predict_proba(X_sample)
    X_sample.to_parquet(ref_dir / "verify_sample.parquet", index=False) if False else X_sample.to_json(
        ref_dir / "verify_sample.json", orient="records", indent=2
    )
    np.save(ref_dir / "verify_proba.npy", proba_ref)
    (ref_dir / "verify_meta.json").write_text(
        json.dumps(
            {
                "registered_model": reg_name,
                "version": mv.version,
                "alias": "champion",
                "run_id": champion_run["run_id"],
                "family": best_family,
                "test_metrics": test_metrics,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\n=== Promotion Model Registry ===")
    print(f"  Modèle enregistré : {reg_name} v{mv.version} (alias: champion)")
    print(f"  Run ID            : {champion_run['run_id']}")
    print(f"  Justification     : {reason}")


def verify_reload(args):
    """Recharge models:/telco-churn@champion dans un processus neuf et compare les prédictions (R10)."""
    ref_dir = Path("data")
    sample_path = ref_dir / "verify_sample.json"
    proba_path = ref_dir / "verify_proba.npy"
    meta_path = ref_dir / "verify_meta.json"

    if not (sample_path.exists() and proba_path.exists() and meta_path.exists()):
        raise FileNotFoundError(
            "Fichiers de référence absents dans ml/data/. Lancer d'abord la campagne avec --promote."
        )

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    X_sample = pd.read_json(sample_path, orient="records")
    for col in NUM_COLS:
        X_sample[col] = X_sample[col].astype("float64")
    for col in CAT_COLS:
        X_sample[col] = X_sample[col].astype(str)
    expected_proba = np.load(proba_path)

    model_uri = f"models:/{args.registered_model_name}@champion"
    print(f"[reload] Chargement depuis {model_uri} ...")
    loaded_pipe = mlflow.sklearn.load_model(model_uri=model_uri)
    reloaded_proba = loaded_pipe.predict_proba(X_sample)

    if not np.allclose(expected_proba, reloaded_proba, atol=1e-7):
        max_diff = float(np.max(np.abs(expected_proba - reloaded_proba)))
        raise AssertionError(f"Écart de prédiction après rechargement : max_diff={max_diff}")

    print(
        f"[OK] Rechargement vérifié pour {model_uri} (version {meta['version']}, "
        f"famille={meta['family']}) : prédictions identiques sur {len(X_sample)} lignes "
        f"(max_diff={float(np.max(np.abs(expected_proba - reloaded_proba))):.2e})."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Entraînement MLflow J3 : Telco Churn (Pipeline complète, validation, champion)"
    )
    parser.add_argument("--dataset", choices=["housing", "churn"], default="churn")
    parser.add_argument(
        "--model",
        choices=["all", "logreg", "rf", "ridge"],
        default="all",
        help="all (logreg + rf sur churn), logreg, rf, ou ridge (housing)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Graine unique (mode housing)")
    parser.add_argument(
        "--seeds",
        default="42,123,2026",
        help="Liste de graines séparées par des virgules (défaut: 42,123,2026)",
    )
    parser.add_argument("--split-seed", type=int, default=42)
    parser.add_argument("--experiment", default=None)
    parser.add_argument("--registered-model-name", default="telco-churn")
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Sélectionner le champion sur validation, évaluer 1 fois sur test et enregistrer",
    )
    parser.add_argument(
        "--verify-reload",
        action="store_true",
        help="Recharger models:/telco-churn@champion dans ce processus et vérifier les prédictions",
    )
    args = parser.parse_args()

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"))

    if args.verify_reload:
        verify_reload(args)
    elif args.dataset == "housing":
        run_housing(args)
    else:
        run_churn_campaign(args)


if __name__ == "__main__":
    main()