# J2 — Bilan, checklist et preuves

**Échéance : 20 novembre 2026, 18 h.** Ce bilan décrit les résultats rapportés dans le dépôt ; il ne constitue pas une validation du professeur.

## Socle J2

- [x] **K3s** : trois serveurs `Ready` sur KVM/libvirt — [journal du 10/11](../journal/2026-11-10.md) et [capture des nœuds](preuves/j2-headlamp-noeuds.png).
- [x] **Longhorn** : trois nœuds prêts ; les trois volumes observés sont `healthy` avec trois réplicas chacun, StorageClass `longhorn-3copies` avec `Retain` — [preuve de persistance](preuves/persistance.md).
- [x] **PostgreSQL persistant** : la table de preuve a été relue après recréation de `postgres-0` — [preuve de persistance](preuves/persistance.md).
- [x] **MinIO déployé sur le cluster** : le journal rapporte un PVC Longhorn, un bucket et un objet ; la [capture MinIO](preuves/minio-interface.png) montre le bucket et l’objet.
- [x] **Persistance MinIO après recréation du pod** : l’objet S3 de preuve a été relu après recréation de `minio-0` — [preuve de persistance](preuves/persistance.md).
- [x] **Capture de la preuve directe** : [sortie du terminal N2](preuves/j2-persistance-postgres-minio-2026-11-20.png).
- [ ] **Reconstruction complète par script** : un orchestrateur existe, mais il n’a pas encore été exécuté sur une cible propre ; le critère n’est donc pas validé. Voir le [guide du socle](../../scripts/j2/README.md).

La preuve PostgreSQL couvre la recréation du pod et la conservation de son PVC. Les trois VM sont hébergées sur le même hôte `n2` ; les réplicas Longhorn ne protègent pas d’une panne de cet hôte.

## MLflow — préparation de J3, hors critères de livraison J2

- [x] POC local : quatre runs sur un serveur MLflow local avec SQLite et artefacts locaux — [README ML](../../ml/README.md) et [captures du POC](preuves/).
- [ ] Serveur MLflow déployé sur K3s : non réalisé selon le [journal du 20/11](../journal/2026-11-20.md).
- [ ] Intégration du serveur MLflow du cluster à PostgreSQL et MinIO, puis premier run : à réaliser pour J3.

Le dépôt prouve actuellement un POC local avec SQLite et des artefacts locaux. Il ne contient pas de preuve du POC « proxy mode + PostgreSQL + MinIO local » ni du fichier `preuves/mlflow-local-postgres.md` ; ne pas présenter cette intégration comme réalisée.

## Versions MinIO

L’image importée sur le cluster est `localhost/minio-j2:2025-10-15`, construite depuis le tag source `RELEASE.2025-10-15T17-29-55Z`. Le digest rapporté pour l’image cluster est `sha256:cdfb4432376519bce450409bb4e12660834a87e4d59e0b3678350ca951a5153b` ; voir [`versions.yaml`](../../versions.yaml). Le digest `sha256:21074a1035...` concerne une variante locale et ne doit pas être présenté comme le digest de l’image déployée sur le cluster.

## Fichiers et procédures présents

- [`reconstruire-j2.sh`](../../scripts/j2/reconstruire-j2.sh) — orchestrateur de reconstruction depuis l’hôte Ubuntu.
- [`preparer-hote.sh`](../../scripts/j2/preparer-hote.sh) — installation des dépendances de l’hôte.
- [`libvirt-default-network.xml`](../../scripts/j2/libvirt-default-network.xml) — réseau NAT `default` créé seulement s’il est absent.
- [`creer-vm.sh`](../../scripts/j2/creer-vm.sh) — création d’une VM.
- [`reserver-ip.sh`](../../scripts/j2/reserver-ip.sh) — réservations DHCP pour les MAC configurées.
- [`installer-k3s.sh`](../../scripts/j2/installer-k3s.sh) — installation de K3s sur trois serveurs.
- [`preparer-longhorn.sh`](../../scripts/j2/preparer-longhorn.sh) et [`installer-longhorn.sh`](../../scripts/j2/installer-longhorn.sh) — prérequis et installation de Longhorn.
- [`longhorn-3copies.yaml`](../../scripts/j2/longhorn-3copies.yaml) — StorageClass Longhorn.
- [`test-longhorn.yaml`](../../scripts/j2/test-longhorn.yaml) — test de volume Longhorn.
- [`postgres.yaml`](../../scripts/j2/postgres.yaml) — Service et StatefulSet PostgreSQL ; le namespace et le Secret sont créés séparément.
- [`build-minio.sh`](../../scripts/j2/build-minio.sh), [`minio.Containerfile`](../../scripts/j2/minio.Containerfile) et [`import-minio.sh`](../../scripts/j2/import-minio.sh) — construction et import de l’image MinIO.
- [`deployer-services.sh`](../../scripts/j2/deployer-services.sh) — Secrets et déploiement de PostgreSQL et MinIO.
- [`minio.yaml`](../../scripts/j2/minio.yaml) — Service et StatefulSet du serveur MinIO.
- [`test-s3.yaml`](../../scripts/j2/test-s3.yaml) et [`verifier-s3.py`](../../scripts/j2/verifier-s3.py) — client et test S3.
- [`verifier-persistance.sh`](../../scripts/j2/verifier-persistance.sh) — vérification avec recréation des pods ; demande une confirmation car elle interrompt brièvement les services.

Le détail et les limites sont dans le [guide du socle](../../scripts/j2/README.md) et la [procédure MinIO](../../scripts/j2/minio-j2.md).
