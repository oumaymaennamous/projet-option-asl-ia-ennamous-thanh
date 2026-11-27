# Preuves MLflow — J3 (23/11, 25/11 et 27/11/2026)

## Vérifié le 23/11/2026
- Release Helm `mlflow` révision 2, chart 3.18.0, statut `deployed`.
- Pod `mlflow` 1/1 Running, 0 redémarrage en 114 min (pod recréé lors du test de persistance), 443 Mi, 4m CPU.
- PostgreSQL : alembic_version `f4a9b2c7d1e6`, 73 tables (schéma public).
- Smoke test : run `4acbe2600f854c29891f3c7ece519836` (écrit le 23/11, artefact `smoke.txt` présent dans `minio-0`). Après chaque suppression successive de `mlflow`, `postgres-0` puis `minio-0`, relecture réussie des paramètres, de la métrique `value=1.0` et de l'artefact.
- Registre : `telco-churn` v1, alias `champion`, run `988f9b535a714b3a936db5cc194258c0` (état du 23/11 ; l'alias a été déplacé sur la v2 le 27/11).
- Rechargement `models:/telco-churn@champion` : prédictions identiques sur 20 lignes (max_diff=0.00e+00), exécuté depuis le poste Windows via tunnel.
- Dataset : sha256 `4cd901ef…6017` (paramètre du run, identique à versions.yaml).
- Image `mlflow:v3.18.0-full` présente sur les 3 nœuds (pré-pull le 23/11, digest identique).

## Vérifié le 25/11/2026
- Pods `mlflow-64b7ff7db8-dqwl7`, `postgres-0`, `minio-0` : 1/1 Running, 0 redémarrage après 42 h (tous sur `k3s-server-3`).
- Appel intra-cluster depuis un pod temporaire : `GET http://mlflow.mlops.svc.cluster.local:5000/health` → HTTP 200 (07:27 UTC). Pas de 403 « Invalid Host header » : `--allowed-hosts` non nécessaire à ce stade. Non testé : nom court `mlflow`, ni un vrai appel de tracking depuis un pod (prévu J4).
- Image `ghcr.io/mlflow/mlflow:v3.18.0-full` présente sur les 3 nœuds (`ctr images ls`).
- Redémarrage de `k3s-server-2` : nœuds `Ready`, volumes Longhorn revenus à `healthy` avec 3 réplicas `running` ; `mlflow`, `postgres-0`, `minio-0` inchangés (0 redémarrage).

## Vérifié le 27/11/2026
- Campagne rejouée dans `p3-churn` : 6 nouveaux runs (commit `ed27aa8`, `ml/src/train.py` identique à celui de `HEAD`, vérifié par `git diff`), en plus des 6 runs du 23/11 (commit `692f1e4`). L'expérience contient donc 12 runs.
- Résultats identiques d'une campagne à l'autre, run par run : `val_f1` logreg 0.6275 (×3), rf 0.6170, 0.6170, 0.6135. Reproductibilité observée sur le même poste, le même venv et le même fichier de données (sha256 identique `4cd901ef…6017`).
- Registre `telco-churn` : v1 (run `988f9b53…`, 23/11) et v2 (run `59b0729f…`, 27/11), tags `val_f1=0.6275` et `test_f1=0.6070` identiques ; l'alias `champion` pointe sur la v2.
- Rechargement de `models:/telco-churn@champion` (v2) : prédictions identiques sur 20 lignes (`max_diff=0.00e+00`).
- Détail de la campagne et sorties : `experiments-j3.md`.

## Résultats (validation 20 %, 3 graines : 42, 123, 2026)
| Famille | médiane val_f1 | IQR | val_recall |
|---|---|---|---|
| logreg | 0.6275 | 0.0000 | 0.7701 |
| rf | 0.6170 | 0.0018 | 0.6872 |
Test (une évaluation par campagne, champion ; résultats identiques le 23/11 et le 27/11) : f1 0.6070, recall 0.7888, roc_auc 0.8348.

Capture de l'expérience `p3-churn` :

![Les six runs du 23/11 (état de l'expérience ce jour-là ; elle en compte douze depuis le 27/11)](j3-mlflow-experiment-churn.png)

## Limites
- Écart logreg/rf d'environ 0,01 de F1 sur une seule partition (`split_seed=42`) : non démontré comme supérieur au bruit du découpage.
- Pour logreg, les graines n'ont eu aucun effet observable sur les métriques (trois runs identiques).
- Tag `git_commit` des runs : `692f1e4` (23/11, sur `main`) et `ed27aa8` (27/11, sur `thanhtu`). `ml/src/train.py` de `692f1e4` est identique à celui de `1193850` ; celui de `ed27aa8` est identique à celui de `HEAD`. Les deux versions ne diffèrent que par une expression morte (`... if False else ...`, retirée en `3cbf255`), sans effet sur le comportement (vérifié par `git diff`).
- Rechargement testé hors cluster ; test dans un Job prévu en J4.
- Licence du dataset : le dépôt IBM `telco-customer-churn-on-icp4d` est sous Apache-2.0 (LICENSE et README, consultés le 25/11/2026) ; le texte vise le « code pattern », sans licence ni copyright distincts pour `Telco-Customer-Churn.csv`. Le paramètre `dataset_license` des runs (« IBM Sample Data / Apache-2.0 ») est une formulation non étayée par ces documents ; non modifiée car les runs sont déjà enregistrés. Usage pédagogique ; CSV non versionné dans notre dépôt.
- Les trois pods (`mlflow`, `postgres-0`, `minio-0`) tournent sur `k3s-server-3` (observation, cause non établie). Aucun test de bascule : prévu le 14/12 (R3).
- DNS des VM : configuration `netplan` fixe (`60-dns.yaml`) appliquée et validée après redémarrage sur `k3s-server-2` uniquement ; contournement manuel (`1.1.1.1`) encore actif sur `k3s-server-1` et `k3s-server-3`, perdu à leur redémarrage. L'image MLflow est présente sur les 3 nœuds ; en revanche, une image absente du cache d'un nœud ne pourrait pas y être tirée après un redémarrage tant que le DNS pérenne n'y est pas en place (hypothèse, non testée).
- Le jeu de test a été évalué deux fois (une fois par campagne). La famille était choisie sur validation et les résultats sont identiques : aucune décision n'a été prise à partir du test.
- `--promote` n'est pas idempotent : chaque exécution crée une version, déplace l'alias `champion` et réévalue le test. Ne pas le relancer avant le tag `j3`.
- Reproductibilité non testée hors du poste Windows et du venv `ml/.venv` (Job du cluster : J4). La v1 reste dans le registre, sans alias.