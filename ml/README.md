# POC MLflow local

POC de suivi d'expériences avec MLflow et scikit-learn. Deux jeux de données : California Housing (régression, POC historique) et Telco Customer Churn (classification binaire, cas d'usage principal du projet). Il valide la chaîne locale de suivi ; l'enregistrement dans le registre, la promotion (alias `champion`) et l'exécution sur K3s restent à faire (J3).

## Versions

Versions testées le 2026-11-05 (`pip freeze`, Python 3.12.10, Windows) : MLflow 3.18.0, scikit-learn 1.5.2, skops 0.16.0, pandas 2.2.3, numpy 1.26.4, scipy 1.17.1, SQLAlchemy 2.0.28. Détail dans [../versions.yaml](../versions.yaml) et `requirements.txt`. Quatre runs exécutés avec succès contre un serveur MLflow local 3.18.0 (SQLite). Le serveur du chart Helm sur le cluster reste à tester.

Les versions du client, du serveur et du chart doivent rester alignées (voir [ADR-002](../docs/adr/ADR-002-stockage-mlflow.md)). Avant un déploiement, vérifier le chart :

```powershell
helm show chart oci://ghcr.io/mlflow/charts/mlflow --version 3.18.0
```

## Lancer le POC

Prérequis : Python 3.12 (testé : 3.12.10). Depuis la racine du dépôt, dans PowerShell :

```powershell
cd ml
python -m venv .venv
.venv\Scripts\Activate.ps1 # Sous Linux/macOS : `source .venv/bin/activate`.
pip install -r requirements.txt
```

Premier terminal, serveur MLflow local (SQLite pour les métadonnées, dossier local pour les artefacts) :

```powershell
mlflow server --host 127.0.0.1 --port 5000 --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlartifacts
```

MLflow 3.x refuse le stockage par fichiers (`./mlruns`) : sans `--backend-store-uri`, le serveur ne démarre pas.

Second terminal, avec le même environnement activé (depuis `ml/`) :

```powershell
# Housing (POC historique, régression)
python src/train.py --dataset housing --model rf
python src/train.py --dataset housing --model ridge

# Churn (cas d'usage J3, classification)
python src/train.py --dataset churn --model logreg
python src/train.py --dataset churn --model rf
```

Interface : http://127.0.0.1:5000. `MLFLOW_TRACKING_URI` permet de viser un autre serveur (par exemple celui déployé sur K3s à J3).

Expériences MLflow : `p3-baseline` (housing : `rmse`, `r2`) et `p3-churn` (churn : `accuracy`, `precision`, `recall`, `f1`, `roc_auc`, `f1_thr_30/50/70`). Noms des runs : `EXP-J3-<dataset>-<modèle>-seed<graine>`.

## Points connus

- MLflow 3.x vérifie les types « de confiance » lors de la sauvegarde d'un modèle scikit-learn : pour un RandomForest (régression ou classification), `log_model` reçoit `skops_trusted_types=["sklearn.tree._tree.Tree"]`. Le rechargement du modèle ailleurs (Job, serving) devra être testé avec la même contrainte.
- Le jeu Telco est téléchargé au premier run depuis un miroir GitHub, puis mis en cache dans `data/telco_churn.csv` (chemin relatif : lancer depuis `ml/`). Source, licence et empreinte restent à documenter (risque R20). Le dossier `ml/data/` n'est pas versionné.
- Le prétraitement (`get_dummies`) est fait avant le découpage et hors de la pipeline sauvegardée : le modèle enregistré attend des colonnes déjà encodées. À corriger avant J3 (risque R10).
- Ces runs sont des références sur le jeu de test avec une seule graine : ils ne servent pas à choisir un `champion` (la sélection se fera sur un jeu de validation).
- Les fichiers `mlflow.db` et `mlartifacts/` ne sont pas versionnés (voir `.gitignore`).
## Captures d'écran

Dans `../docs/jalons/preuves/` :

| Fichier | Contenu | Version client |
|---|---|---|
| `poc-mlflow-experiment.png` | Expérience `p3-baseline` (Housing) | 3.18.0 |
| `poc-mlflow-run-rf.png` | Run Housing RandomForest | 3.18.0 |
| `poc-mlflow-run-ridge.png` | Run Housing Ridge | 3.18.0 |
| `poc-mlflow-experiment-churn.png` | Expérience `p3-churn` | 3.18.0 |
| `poc-mlflow-churn-logreg.png` | Run Churn LogisticRegression | 3.18.0 |
| `poc-mlflow-churn-rf.png` | Run Churn RandomForest | 3.18.0 |
| `poc-mlflow-churn-rf-artifacts.png` | Vue artifacts (model, signature) | 3.18.0 |

Les captures Housing sont conservées comme preuve historique du premier POC.