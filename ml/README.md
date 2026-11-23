# Entraînement et suivi MLflow (POC local & J3 cluster)

Chaîne d'entraînement et de suivi d'expériences avec **MLflow 3.18.0** et **scikit-learn 1.5.2**. Deux jeux de données : **Telco Customer Churn** (classification binaire, cas d'usage principal J3) et **California Housing** (régression, POC historique).

## Versions

Versions testées le 2026-11-05 (`pip freeze`, Python 3.12.10, Windows) : MLflow 3.18.0, scikit-learn 1.5.2, skops 0.16.0, pandas 2.2.3, numpy 1.26.4, scipy 1.17.1, SQLAlchemy 2.0.28. Détail dans [`../versions.yaml`](../versions.yaml) et [`requirements.txt`](requirements.txt).

Les versions du client, du serveur et du chart doivent rester alignées (voir [`ADR-002`](../docs/adr/ADR-002-stockage-mlflow.md)).

## Installation de l'environnement

Prérequis : Python 3.12 (testé : 3.12.10). Depuis la racine du dépôt, dans PowerShell :

```powershell
cd ml
python -m venv .venv
.venv\Scripts\Activate.ps1 # Sous Linux/macOS : `source .venv/bin/activate`.
pip install -r requirements.txt
```

## Exécuter la campagne J3 (Telco Customer Churn)

### 1. Cible serveur MLflow

- **Cluster K3s (`n2`)** : ouvrir d'abord les deux tunnels SSH/`port-forward` décrits dans [`../scripts/j3/README.md`](../scripts/j3/README.md), puis viser `http://127.0.0.1:5000`.
- **Serveur local de secours** :

```powershell
mlflow server --host 127.0.0.1 --port 5000 --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlartifacts
```

### 2. Entraînement comparatif, promotion `champion` et rechargement

Depuis `ml/` avec `.venv` activé :

```powershell
$env:MLFLOW_TRACKING_URI = "http://127.0.0.1:5000"

# Campagne J3 : 6 runs (logreg vs rf sur graines 42, 123, 2026),
# sélection sur validation (60/20/20), évaluation unique sur test et enregistrement @champion
python src/train.py --dataset churn --model all --seeds 42,123,2026 --promote

# Vérification du rechargement indépendant depuis le Model Registry
python src/train.py --verify-reload

# POC historique (California Housing, régression)
python src/train.py --dataset housing --model rf
python src/train.py --dataset housing --model ridge
```

Expériences MLflow : `p3-churn` (métriques `val_*` et `test_*` pour le champion) et `p3-baseline` (`rmse`, `r2` pour Housing). Modèle enregistré : `telco-churn` (alias `champion`).

## Détails techniques (J3)

- **Pipeline sans fuite de données (R9/R10)** : `ColumnTransformer` (`StandardScaler` + `OneHotEncoder(handle_unknown="ignore")`) intégré à l'intérieur de la `Pipeline` scikit-learn ; découpage stratifié **60% train / 20% validation / 20% test**.
- **Sérialisation `skops`** : MLflow 3.18.0 exige `skops_trusted_types=["sklearn.compose._column_transformer._RemainderColsList", "sklearn.tree._tree.Tree"]` lors de l'appel à `log_model` pour une pipeline contenant un `ColumnTransformer` et/ou un `RandomForest`. Au rechargement (`mlflow.sklearn.load_model`), MLflow relit cette liste depuis les métadonnées `MLmodel`.
- **Jeu de données Telco Churn (R20)** : téléchargé automatiquement depuis le miroir GitHub IBM (`Telco-Customer-Churn.csv`) dans `ml/data/telco_churn.csv` (non versionné) ; sa source, sa licence et son empreinte SHA-256 sont journalisées dans les paramètres de chaque run.

## Captures d'écran

Dans [`../docs/jalons/preuves/`](../docs/jalons/preuves/) :

- **Cluster K3s (J3)** : [`j3-mlflow-experiment-churn.png`](../docs/jalons/preuves/j3-mlflow-experiment-churn.png), [`j3-mlflow-run-champion.png`](../docs/jalons/preuves/j3-mlflow-run-champion.png), [`j3-mlflow-registry-champion.png`](../docs/jalons/preuves/j3-mlflow-registry-champion.png).
- **POC local initial (05/11)** : [`poc-mlflow-experiment.png`](../docs/jalons/preuves/poc-mlflow-experiment.png), [`poc-mlflow-run-rf.png`](../docs/jalons/preuves/poc-mlflow-run-rf.png), [`poc-mlflow-run-ridge.png`](../docs/jalons/preuves/poc-mlflow-run-ridge.png), [`poc-mlflow-experiment-churn.png`](../docs/jalons/preuves/poc-mlflow-experiment-churn.png), [`poc-mlflow-churn-logreg.png`](../docs/jalons/preuves/poc-mlflow-churn-logreg.png), [`poc-mlflow-churn-rf.png`](../docs/jalons/preuves/poc-mlflow-churn-rf.png), [`poc-mlflow-churn-rf-artifacts.png`](../docs/jalons/preuves/poc-mlflow-churn-rf-artifacts.png).