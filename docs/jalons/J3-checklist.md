# J3 — Checklist et preuves

**Échéance : 15 décembre 2026, 18 h.** Cette checklist décrit l'état des preuves ; elle ne vaut pas validation du professeur.

## Preuves versées
- [x] MLflow 3.18.0 déployé sur K3s (Helm, mode proxy, PostgreSQL + MinIO) — `preuves/mlflow.md`, `scripts/j3/`
- [x] Schéma PostgreSQL créé (alembic `f4a9b2c7d1e6`, 73 tables) — `preuves/mlflow.md`
- [x] Persistance bout en bout après suppression de `mlflow`, `postgres-0`, `minio-0` — `journal/2026-11-23.md`
- [x] 6 runs comparés (logreg vs rf, 3 graines, 60/20/20) dans `p3-churn` — `j3-mlflow-experiment-churn.png`
- [x] Modèle `telco-churn` v1, alias `champion`, avec justification — `j3-mlflow-registry-champion.png`
- [x] Rechargement `@champion` identique (max_diff 0) — `preuves/mlflow.md`
- [x] Source, sha256 du dataset journalisés ; licence des données non établie (R20 : documenté avec réserve) — `preuves/mlflow.md`
- [x] Appel intra-cluster `/health` : 200 — `preuves/mlflow.md`

## À terminer avant le tag
- [ ] Revue croisée (Oumayma, Marwa)
- [ ] Journaux 27/11, 14/12, 15/12 (25/11 : `journal/2026-11-25.md`)
- [ ] Licence propre aux données du dataset : non trouvée ; décider avec le groupe de la conserver telle quelle (usage pédagogique)
- [ ] Merge dans `main` puis tag `j3` (minuscule) avant le 15/12 18 h

## Limites connues
- Écart logreg/rf faible, une seule partition ; rechargement testé hors cluster ; DNS contourné à la main (perdu au reboot) ; 3 pods sur `k3s-server-3` ; failover non testé (R3 : diffusé prévu 14/12).