# Déployer et vérifier MLflow sur le cluster K3s — J3

Ce dossier regroupe les manifestes Helm et scripts permettant de déployer le serveur **MLflow 3.18.0** en mode proxy sur le cluster K3s (`n2`), connecté à **PostgreSQL 16** (métadonnées et registre) et **MinIO** (artefacts S3 dans `s3://mlflow-artifacts`).

## Contenu du dossier

- [`values-j3.yaml`](values-j3.yaml) — valeurs Helm pour le chart officiel `oci://ghcr.io/mlflow/charts/mlflow` (`3.18.0`) : mode proxy (`serve_artifacts`), `workers: 1`, désactivation de l'exécuteur de tâches (`MLFLOW_SERVER_ENABLE_JOB_EXECUTION=false` et `MLFLOW_SERVER_JOB_ENABLE_PERIODIC_TASKS=false`), limite mémoire à `768Mi`.
- [`installer-mlflow.sh`](installer-mlflow.sh) — script idempotent exécuté depuis `n2` : vérifie la résolution DNS sur les trois VM, installe Helm `v3.22.1` (empreinte SHA-256 figée), crée le Secret `mlflow-db` s'il manque à partir de `postgres-auth`, valide avec `--dry-run=server` puis exécute `helm upgrade --install --wait`.
- [`smoke-test.py`](smoke-test.py) — script client de vérification bout-en-bout (`write` et `read <run_id>`).

## Prérequis

- Socle J2 opérationnel sur `n2` (`172.19.3.42`) : trois nœuds K3s `Ready`, Longhorn `longhorn-3copies`, StatefulSets `postgres` et `minio` `Running` dans le namespace `mlops`, Secrets `postgres-auth` et `minio-secret` présents, bucket `mlflow-artifacts` créé.
- Clé SSH `~/.ssh/mlops-j2` disponible sur `n2`.

## 1. Déployer MLflow depuis `n2`

```bash
bash scripts/j3/installer-mlflow.sh
```

Vérifier l'état du pod, de la consommation mémoire et du schéma PostgreSQL :

```bash
ssh -i ~/.ssh/mlops-j2 ubuntu@192.168.122.53 '
  sudo -n k3s kubectl -n mlops get pods,svc -o wide &&
  sudo -n k3s kubectl top pods -n mlops &&
  sudo -n env KUBECONFIG=/etc/rancher/k3s/k3s.yaml helm list -n mlops
'
```

## 2. Accéder à l'interface et à l'API depuis Windows

1. **Terminal A (sur `n2`)** — ouvrir le relais vers le service `mlflow` du cluster (laisser ouvert) :

```bash
ssh -o ExitOnForwardFailure=yes -i ~/.ssh/mlops-j2 \
  -L 127.0.0.1:15000:127.0.0.1:5000 ubuntu@192.168.122.53 \
  'sudo -n k3s kubectl -n mlops port-forward --address 127.0.0.1 svc/mlflow 5000:5000'
```

2. **Terminal B (PowerShell sur Windows)** — ouvrir le second relais vers `n2` (laisser ouvert) :

```powershell
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:5000:127.0.0.1:15000 ops@172.19.3.42
```

3. **Terminal C (PowerShell sur Windows, depuis `ml/` avec `.venv` activé)** — tester `/health` et exécuter le test bout-en-bout :

```powershell
curl.exe -i http://127.0.0.1:5000/health
$env:MLFLOW_TRACKING_URI = "http://127.0.0.1:5000"
python ..\scripts\j3\smoke-test.py write
python ..\scripts\j3\smoke-test.py read <run_id>
```

Interface web accessible sur `http://127.0.0.1:5000`.