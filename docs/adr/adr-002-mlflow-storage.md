# ADR-002 — Stockage de MLflow : base de données et artefacts

- Date : 2026-11-04
- Statut : proposé (à valider par Oumayma et Marwa)
- Auteur : Thanh Tu Vo

## Contexte
MLflow a besoin de deux stockages : un backend store (runs, paramètres, métriques, registre de modèles) et un artifact store (modèles, graphiques, fichiers). J2 (20/11) exige PostgreSQL et MinIO déployés avec stockage persistant ; MLflow sur le cluster est attendu à J3 (15/12). Les volumes k3s par défaut (`local-path`) sont attachés à un nœud (voir ADR-001).

## Options : backend store

### A. SQLite
- + Aucune infrastructure, suffisant pour le POC local
- − Un seul écrivain à la fois, peu adapté aux accès concurrents (plusieurs Jobs)
- − Fichier à placer sur un volume persistant pour survivre au redémarrage d'un pod

### B. PostgreSQL
- + Accès concurrents, transactions, adapté à plusieurs clients et au registre
- − Un PVC, des sauvegardes et des identifiants (Secret) à gérer

Décision : SQLite pour le POC local, PostgreSQL sur le cluster.

## Options : artifact store

### A. Volume local (PVC)
- + Simple, aucune dépendance supplémentaire
- − Attaché à un nœud, non partageable proprement avec d'autres composants (Jobs, extension de serving)

### B. MinIO (compatible S3)
- + API S3 standard, accès partagé par MLflow, les Jobs et une éventuelle extension de serving
- + Séparation claire entre fichiers binaires et métadonnées
- − Un composant de plus, un PVC et des identifiants à gérer

Décision : MinIO sur le cluster ; dossier local `./mlruns` pour le POC.

## Décision consolidée
| Environnement | Backend store | Artifact store |
|---|---|---|
| POC local (poste de travail) | SQLite | `./mlruns` |
| J2 (20/11) | PostgreSQL et MinIO déployés, PVC testés | n/a |
| J3 (15/12) | MLflow sur le cluster : PostgreSQL | MinIO (S3) |

## Conséquences
- Migration SQLite vers PostgreSQL à préparer avant J3 (15/12) et testée sur un cluster local.
- Secrets Kubernetes pour PostgreSQL et MinIO ; aucune valeur dans Git.
- Mode d'accès aux artefacts : à choisir (MLflow en proxy avec `--serve-artifacts`, ou accès direct du client à MinIO). Le proxy évite de distribuer les identifiants MinIO aux clients.
- Déploiement par chart Helm ou manifests : à décider après vérification des charts disponibles (chart MLflow : à vérifier).
- **Versions vérifiées le 2026-11-04** :
  - Chart Helm officiel : `oci://ghcr.io/mlflow/charts/mlflow`, version
    **3.18.0** (vérifiée via `helm show chart`, appVersion = chart version).
  - Client MLflow : **3.18.0** (`ml/requirements.txt`), aligné avec le
    serveur déployé par le chart.
  - POC local retesté avec succès : 2 runs (RandomForest + Ridge) loggés
    via l'API 3.18.0, artifacts visibles dans l'UI.
  - SQLAlchemy fixé à 2.0.28 (bug connu `FallbackAsyncAdaptedQueuePool`
    sur versions intermédiaires).

- **Règle de lock-step** : la version du **chart**, de l'**image serveur**
  et du **client** doivent partager la même version majeure.mineure.
  Vérification à faire à chaque déploiement (checklist J3) :
  `helm show chart oci://ghcr.io/mlflow/charts/mlflow --version X.Y.Z`
  doit correspondre à `mlflow==X.Y.Z` dans `ml/requirements.txt`.
- Sauvegardes de PostgreSQL et MinIO hors de la VM : mécanisme à décider