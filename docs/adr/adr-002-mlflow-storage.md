# ADR-002 - Stockage MLflow

## Contexte
MLflow a 2 stockages : backend (runs/registry) + artifact (modèles/plots).

## Options - Backend
### A. SQLite
- Simple, 0 infra, POC local OK
-  Single-writer, perd l'état au redémarrage du pod
### B. PostgreSQL
- Multi-user, transactionnel, production-ready
- PVC, backup, secret à gérer

→ Décision : SQLite en POC, PostgreSQL en cluster.

## Options - Artifact
### A. Volume local
- Simple
- Non partageable, incompatible avec le chart Helm MLflow officiel
### B. MinIO (S3-compatible)
- API S3 standard, chart Helm MLflow natif, réutilisable pour datasets
- PVC à gérer

→ Décision : MinIO.

## Décision finale
| Env | Backend | Artifacts |
|---|---|---|
| POC (laptop) | SQLite | ./mlruns |
| Cluster (J3) | PostgreSQL 16 | MinIO S3 |

## Conséquences
- Migration SQLite → PG avant J3 (15/12).
- Secrets : `mlflow-db-secret`, `minio-credentials` (jamais en Git).
- versions.yaml : mlflow 2.16.2, postgres 16, minio RELEASE-2024-xx.
- Chart Helm officiel `oci://ghcr.io/mlflow/charts/mlflow`.

## Plan B
Si MinIO échoue → volume local + `mlflow server --serve-artifacts` (moins scalable, documenté).
Si PostgreSQL échoue → SQLite + PVC snapshot (documenté comme limite).