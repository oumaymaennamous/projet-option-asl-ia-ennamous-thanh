# ADR-002 — PostgreSQL, MinIO et volumes Longhorn

- Date : 5 novembre 2026.
- Statut : proposé (à valider par le groupe). Architecture retenue pour le POC ; validation et reconstruction sur KVM à réaliser.
- Auteurs : Oumayma Ennamous (laboratoire VMware, Longhorn, MinIO), Thanh Tu Vo (POC MLflow, versions).

## Contexte

MLflow a besoin de deux stockages : un backend store (runs, paramètres, métriques, registre de modèles) et un artifact store (modèles, graphiques, fichiers). J2 (20/11) exige PostgreSQL et MinIO avec stockage persistant ; J3 (15/12) exige un serveur MLflow et un registre. Les données doivent survivre au remplacement d'un pod ; la reprise sur un autre nœud est un objectif complémentaire.

## Options comparées

### Backend store et artifact store

| Option | Avantages | Limites |
|---|---|---|
| PostgreSQL + MinIO | Sépare SQL et objets S3 ; accès concurrents ; conforme au sujet | Deux services à exploiter, sauvegarder et sécuriser |
| SQLite + fichiers locaux | Très simple pour un essai local | Un seul écrivain ; ne remplit pas la cible J2 ; MLflow 3.x refuse le stockage par fichiers seul |
| PostgreSQL + stockage objet externe | Externalise une partie de l'exploitation | Dépendances réseau, coût, accès ; moins autonome |

### Volumes Kubernetes

| Option | Avantages | Limites |
|---|---|---|
| `local-path` (fourni par K3s) | Simple, aucun composant en plus | Volume lié à un nœud ; pas de reprise sur un autre nœud |
| Longhorn | Réplication entre nœuds, rattachement possible ailleurs | Ressources, espace disque (environ trois fois les données) et exploitation supplémentaires |
| NFS externe | Simple à raccorder | Le serveur NFS devient critique sans redondance propre |

## Décision

- MLflow stocke les métadonnées, expériences et registre dans PostgreSQL.
- MLflow transfère les modèles et artefacts vers le bucket MinIO `mlflow-artifacts`, en mode proxy.
- Un StatefulSet pour PostgreSQL et un pour MinIO, une instance chacun, avec Services internes.
- PVC distincts en classe `longhorn-3copies` : `numberOfReplicas: 3`, anti-affinité stricte des réplicas par nœud, `Retain`, expansion autorisée, moteur V1.
- Le POC utilise 2 Gio par PVC ; dimensionnement final après mesure.

| Environnement | Backend store | Artifact store |
|---|---|---|
| POC local (poste de travail) | SQLite (`sqlite:///mlflow.db`) | `./mlartifacts` |
| J2 (20/11) | PostgreSQL et MinIO déployés, persistance prouvée sur le cluster (PG 10/11, MinIO 18/11) | n/a |
| J3 (15/12) | MLflow sur le cluster avec PostgreSQL | MinIO (S3) |

Points de vigilance : `ReadWriteOnce` ne signifie pas une seule copie de stockage. La réplication Longhorn ne réplique pas PostgreSQL au niveau SQL, et la reprise peut être interrompue. Les trois réplicas sont sur les trois VM d'un même hôte physique : ils protègent d'une panne de VM ou de nœud, pas d'une panne de disque ou de la machine physique.

## Conséquences

- Migration SQLite vers PostgreSQL à préparer avant J3 et à tester sur un cluster local (risque R16).
- Secrets Kubernetes pour PostgreSQL et MinIO ; aucune valeur dans Git.
- Mode d'accès aux artefacts : proxy par le serveur MLflow, ce qui évite de distribuer les identifiants MinIO aux clients.
- Déploiement de MLflow par le chart Helm officiel (voir ci-dessous) ; PostgreSQL et MinIO sont à déployer séparément.
- Le serveur MLflow utilisera temporairement le Secret `minio-secret` (compte root MinIO). Amélioration prévue : utilisateur S3 dédié, limité au bucket `mlflow-artifacts`.

## Versions et compatibilité MLflow

Vérifié le 2026-11-04 (chart) et le 2026-11-05 (client) :

- **Chart Helm** : `oci://ghcr.io/mlflow/charts/mlflow`, version 3.18.0, `appVersion` 3.18.0 (`helm show chart`). Le chart ne déploie que MLflow. Par défaut, le tag de l'image `ghcr.io/mlflow/mlflow` suit `appVersion` ; le tag exact est à confirmer avec `helm template`.
- **Client Python** : MLflow 3.18.0, scikit-learn 1.5.2, skops 0.16.0, pandas 2.2.3, numpy 1.26.4, scipy 1.17.1, SQLAlchemy 2.0.28, Python 3.12.10 (`pip freeze`, détail dans `versions.yaml` et `ml/requirements.txt`).
- **Constaté au POC local** : MLflow 3.x refuse le stockage par fichiers (`./mlruns`) et exige un backend base de données ; il exige aussi `skops_trusted_types=["sklearn.tree._tree.Tree"]` pour enregistrer un RandomForest (régression ou classification). Le rechargement du modèle dans un Job ou un serving devra être testé avec la même contrainte.
- **Règle proposée** : chart, image du serveur et client alignés sur la même version, à vérifier à chaque déploiement : `helm show chart oci://ghcr.io/mlflow/charts/mlflow --version X.Y.Z` doit correspondre à `mlflow==X.Y.Z` dans `ml/requirements.txt`. Un écart de versions est un risque (R15) ; il n'a pas été testé.
- **Configuration du chart prévue** : URI de la base via `mlflow.backendStoreUriFrom` (Secret), identifiants S3 via `env` depuis un Secret, artefacts en mode proxy (`server.flag_options: [serve_artifacts]` et `mlflow.artifactsDestination`).
- **À vérifier** : présence des pilotes PostgreSQL (psycopg2) et S3 (boto3) dans l’image du serveur MLflow.
## Sauvegardes et validation

Sauvegarder PostgreSQL de façon cohérente (par exemple `pg_dump` pour la petite base), les objets et la configuration MinIO et les identifiants (procédure sécurisée), sur une cible indépendante de l'hôte. Les snapshots Longhorn ne suffisent pas. La restauration doit être testée. La cible de sauvegarde est à décider avant J2.

**Preuves du POC MLflow local (versées)** : quatre runs sur un serveur local 3.18.0 (SQLite) : housing (RandomForest, Ridge) et churn (régression logistique, RandomForest). Captures dans `docs/jalons/preuves/` :
`poc-mlflow-experiment.png`, `poc-mlflow-experiment-churn.png`, `poc-mlflow-run-rf.png`, `poc-mlflow-run-ridge.png`, `poc-mlflow-churn-logreg.png`, `poc-mlflow-churn-rf.png`, `poc-mlflow-churn-rf-artifacts.png`.

**Cluster KVM/libvirt de l'école (versées)** : PostgreSQL (10/11) et MinIO (18/11) conservent leurs données après suppression du pod ; les volumes `data-postgres-0` et `data-minio-0` ont chacun trois répliques `running` sur les trois nœuds (contrôle du 20/11). Détail dans `docs/jalons/preuves/persistance.md`.

**Laboratoire VMware (déclaré, preuves à verser)** : données SQL et objet S3 retrouvés après recréation du pod ; trois copies actives vérifiées pour un volume de test. À verser : preuves SQL et S3, santé et placement des réplicas des volumes applicatifs, test de reprise contrôlé et restauration. Ne pas forcer un détachement avant d'avoir confirmé l'arrêt de l'ancien écrivain.

## Plan B

Déclencheur à fixer ensemble avant J2 : date à laquelle PostgreSQL et MinIO doivent être Ready avec données conservées après recréation des pods.

- **Longhorn** : si Longhorn empêche durablement J2 (capacité, compatibilité), conserver PostgreSQL et MinIO avec des PVC `local-path` et des sauvegardes hors hôte, en assumant l'indisponibilité si le nœud portant le volume tombe. Une migration ultérieure exige copie, restauration et vérification des données ; changer la StorageClass par défaut ne migre pas les PVC existants.
- **MinIO** : MinIO ne publie plus d'images Docker officielles ; `Dockerfile.release` renvoie HTTP 410 et le Dockerfile officiel dépend de `minio/minio:latest`, inexistante sur Docker Hub (dépendance circulaire). **Solution déployée le 18/11/2026** : image `localhost/minio-j2:2025-10-15`, construite sur n2 avec Podman en deux étapes (`golang:1.24-alpine` puis `alpine:3.23`) ; le binaire est compilé par `go install github.com/minio/minio@RELEASE.2025-10-15T17-29-55Z`. L'archive `minio-j2.tar` (~153 Mo) est importée dans le containerd des trois VM (digest `sha256:cdfb4432376519bce450409bb4e12660834a87e4d59e0b3678350ca951a5153b`, identique sur les trois nœuds) et le StatefulSet utilise `imagePullPolicy: Never`. Les identifiants sont fournis au runtime par le Secret `minio-secret` ; aucun n'est dans l'image. **Limites** : le tag source fixe la version mais le commit n'est pas vérifié (le binaire affiche `DEVELOPMENT.GOGET`) ; les images de base sont des tags flottants ; l'import est manuel. Pour J5 : registre local `registry:2` sur n2:5000 ou CI, et bases épinglées par digest. Procédure : `scripts/j2/minio-j2.md`. Une variante construite sous WSL2 (commit `9e49d5e…` vérifié, base alpine 3.22, digest local `sha256:21074a10…`) a été testée en Docker local uniquement ; elle est archivée dans `docs/archive/minio-wsl2/`.
- **PostgreSQL** : si l'instance est instable, SQLite sur un PVC avec snapshot est un repli temporaire, avec ses limites documentées (un seul écrivain).
- **Artefacts** : en dernier recours, artefacts sur un PVC servis par MLflow en mode proxy, limite documentée (lié à un nœud).