# Preuves MLflow — J3 (23/11/2026)

## Vérifié le 23/11/2026
- Release Helm `mlflow` révision 2, chart 3.18.0, statut `deployed`.
- Pod `mlflow` 1/1 Running, 0 redémarrage en 114 min (pod recréé lors du test de persistance), 443 Mi, 4m CPU.
- PostgreSQL : alembic_version `f4a9b2c7d1e6`, 73 tables (schéma public).
- Smoke test : run `4acbe2600f854c29891f3c7ece519836` relu (params, métrique value=1.0, artefact smoke.txt) après suppression de `mlflow`, `postgres-0`, `minio-0`, et relu de nouveau le 23/11.
- Registre : `telco-churn` v1, alias `champion`, run `988f9b535a714b3a936db5cc194258c0`.
- Rechargement `models:/telco-churn@champion` : prédictions identiques sur 20 lignes (max_diff=0.00e+00), exécuté depuis le poste Windows via tunnel.
- Dataset : sha256 `4cd901ef…6017` (paramètre du run, identique à versions.yaml).
- Image `mlflow:v3.18.0-full` présente sur les 3 nœuds (pré-pull le 23/11, digest identique).

## Résultats (validation 20 %, 3 graines : 42, 123, 2026)
| Famille | médiane val_f1 | IQR | val_recall |
|---|---|---|---|
| logreg | 0.6275 | 0.0000 | 0.7701 |
| rf | 0.6170 | 0.0018 | 0.6872 |
Test (une seule évaluation, champion) : f1 0.6070, recall 0.7888, roc_auc 0.8348.

Six runs de l'expérience `p3-churn` :

![Les six runs comparatifs dans l'interface MLflow](j3-mlflow-experiment-churn.png)

## Limites
- Écart logreg/rf d'environ 0,01 de F1 sur une seule partition (`split_seed=42`) : non démontré comme supérieur au bruit du découpage.
- Pour logreg, les graines changent peu le résultat : IQR=0 ne prouve pas la stabilité.
- Tag `git_commit` des runs : `692f1e4` (commit présent sur `main`; `ml/src/train.py` identique à `1193850`).
- Rechargement testé hors cluster ; test dans un Job prévu en J4.
- Licence du dataset (Apache-2.0) non recoupée avec le dépôt IBM : à vérifier.