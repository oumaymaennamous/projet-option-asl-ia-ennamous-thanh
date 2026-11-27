# J3 — Checklist et preuves

**Échéance : 15 décembre 2026, 18 h.** Cette checklist décrit l'état des preuves ; elle ne vaut pas validation du professeur.

## Preuves versées
- [x] MLflow 3.18.0 déployé sur K3s (Helm, mode proxy, PostgreSQL + MinIO) — `preuves/mlflow.md`, `scripts/j3/`
- [x] Schéma PostgreSQL créé (alembic `f4a9b2c7d1e6`, 73 tables) — `preuves/mlflow.md`
- [x] Persistance bout en bout après suppression de `mlflow`, `postgres-0`, `minio-0` — `journal/2026-11-23.md`
- [x] 12 runs comparés (2 campagnes de 6 : logreg vs rf, 3 graines, 60/20/20) dans `p3-churn` — `experiments-j3.md`, `j3-mlflow-experiment-churn.png` (état du 23/11)
- [x] Modèle `telco-churn` enregistré (v1 le 23/11, v2 le 27/11) ; alias `champion` sur la v2, avec justification — `j3-mlflow-registry-champion.png` (état du 23/11), `experiments-j3.md`
- [x] Rechargement `@champion` identique (max_diff 0), constaté le 23/11 (v1) et le 27/11 (v2) — `preuves/mlflow.md`
- [x] Reproductibilité : campagne rejouée le 27/11, métriques identiques run par run (même poste, venv et données) — `preuves/mlflow.md`
- [x] Source, sha256 du dataset journalisés ; licence des données non établie (R20 : documenté avec réserve) — `preuves/mlflow.md`
- [x] Appel intra-cluster `/health` : 200 — `preuves/mlflow.md`

## À terminer avant le tag
- [ ] Revue croisée (Oumayma, Marwa)
- [ ] Journaux 14/12, 15/12 (25/11 et 27/11 rédigés)
- [ ] Licence propre aux données du dataset : non trouvée ; décider avec le groupe de la conserver telle quelle (usage pédagogique)
- [ ] Merge dans `main` puis tag `j3` (minuscule) avant le 15/12 18 h
- [ ] DNS pérenne : répliquer `60-dns.yaml` sur `k3s-server-1` et `k3s-server-3` et valider après redémarrage
- [ ] Décider de la casse des tags (`J2` / `j1`) avant de poser `j3`

## Limites connues
- Écart logreg/rf faible, une seule partition ; rechargement testé hors cluster ; DNS pérenne validé sur `k3s-server-2` seulement (contournement manuel sur les deux autres) ; 3 pods sur `k3s-server-3` ; failover non testé (R3 : exercice contrôlé prévu le 14/12).
- Test évalué une fois par campagne (2 campagnes) ; `--promote` non idempotent (ne pas relancer avant le tag) ; reproductibilité vérifiée sur un seul poste.