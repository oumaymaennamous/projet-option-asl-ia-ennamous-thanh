# J2 — Checklist et preuves

**Échéance : 20 novembre 2026, 18 h.**

## Preuves versées

- [x] K3s 3 serveurs Ready — `journal/2026-11-10.md`
- [x] Longhorn 3 réplicas sur 3 VM — `journal/2026-11-10.md`
- [x] PostgreSQL persistance cluster — `preuves/persistance.md`
- [x] MinIO persistance locale (volume survit recréation conteneur) — `preuves/persistance.md`
- [x] MinIO persistance cluster 
- [x] MLflow déployé sur cluster

## Notes techniques

- Image MinIO figée : `RELEASE.2025-10-15T17-29-55Z`,
  digest `sha256:21074a1035...` (ADR-002, `versions.yaml`)
- Pièges documentés dans `preuves/mlflow-local-postgres.md` :
  - `--default-artifact-root s3://` incompatible avec proxy mode
  - soft-delete MLflow 3.x bloque la réutilisation du nom d'expérience
  - format XL MinIO (`.xl.meta`) pour les objets
  - console MinIO : port aléatoire sans `--console-address`

## Scripts J2 disponibles

- `scripts/j2/creer-vm.sh` — création VM KVM 
- `scripts/j2/installer-k3s.sh` — installation k3s 3 serveurs
- `scripts/j2/preparer-longhorn.sh` — Longhorn
- `scripts/j2/postgres.yaml` — manifest PostgreSQL
- `scripts/j2/minio.yaml` — manifest MinIO de référence J5
- `scripts/j2/minio-Dockerfile.custom` — Dockerfile MinIO custom
- `scripts/j2/build-minio.sh` — build reproductible
- `scripts/j2/import-minio.sh` — import sur 3 VM
