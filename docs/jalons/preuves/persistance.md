# Preuves de persistance — J2

## PostgreSQL — cluster KVM/Longhorn (10/11/2026, session école)

Test réalisé sur n2 (3 VM Ubuntu 24.04, k3s v1.37.2, Longhorn v1.13.0).

- Image : `postgres:16`, StatefulSet `postgres`, namespace `mlops`
- PVC : `data-postgres-0`, StorageClass `longhorn-3copies`, 2 GiB
- Test : table `preuve_j2` + 1 ligne, `kubectl delete pod postgres-0`,
  StatefulSet recrée, requête → `PostgreSQL : donnees conservees`
- Volume Longhorn : 3 réplicas `running` sur 3 VM distinctes

Preuves : `j2-headlamp-noeuds.png`, `j2-headlamp-apercu.png`, `j2-headlamp-pods.png`.

### Limite partagée n2
Les 3 réplicas Longhorn sont sur les 3 VM du même hôte `n2` : protège
d'une panne VM/nœud, pas d'une panne de n2 ni de disque.

## PostgreSQL et MinIO — vérification automatisée sur le cluster n2 (20/11/2026)

Avant le test, les trois VM et les nœuds K3s étaient actifs. Longhorn
v1.13.0 utilisait la StorageClass `longhorn-3copies` (`Retain`) ; les
trois volumes observés étaient `healthy`, avec trois réplicas chacun.
Les PVC `data-postgres-0` et `data-minio-0` étaient `Bound`, chacun de 2 GiB.

Le script `scripts/j2/verifier-persistance.sh --confirm-interruption` a écrit
des données de preuve, recréé les deux pods StatefulSet, puis relu ces données :

- PostgreSQL : table `preuve_j2_20261120152649_36843`, recréation de
  `postgres-0`, puis lecture de `PostgreSQL J2 : donnees conservees`.
- MinIO : objet
  `s3://mlflow-artifacts/preuves/preuve_j2_20261120152649_36843.txt`,
  recréation de `minio-0`, puis lecture de `MinIO J2 : donnees conservees`.
- Résultat du script : les deux rollouts se sont terminés ; le pod client de
  test a été supprimé après la vérification.

Le test n'a supprimé aucun PVC ni aucune donnée existante. La table de preuve
et l'objet S3 créés sont conservés dans le cluster. La sortie du terminal N2
est conservée dans la [capture de persistance du 20/11](j2-persistance-postgres-minio-2026-11-20.png).

---

## MinIO — test persistance local (Docker Desktop, 19/11/2026)

### Configuration
- Conteneur `minio-test`, image custom `sha256:21074a1035...`,
  volume nommé `minio-test-data` monté sur `/data`
- Ports : `9000` (S3 API), `9001` (console)

### Test "delete pod + recreate"

1. Bucket `mlflow-artifacts` créé
2. Run MLflow `p3-churn-persist` (exp id=3, run `c821d790...`)
   → 7 artefacts sous `3/models/m-853f236dd2c14e6d93d07b9734136c1d/artifacts/`
3. Vérifier dans le volume :
   `docker run --rm -v minio-test-data:/data alpine find /data/mlflow-artifacts -type f`
   → 7 fichiers (format XL MinIO : `.xl.meta`)
4. `docker rm -f minio-test` (simule suppression du pod)
5. Recréer avec **le même volume** `-v minio-test-data:/data`
6. Revérifier :
   - `find` : mêmes 7 fichiers `.xl.meta`, timestamps inchangés (21:20:13)
   - `aws s3 ls --recursive s3://mlflow-artifacts/` : 7 objets avec noms
     et tailles corrects (`MLmodel` 3300, `model.skops` 36565, ...)

**Résultat : données survivent à la recréation du conteneur.**

Preuves : `poc-minio-persist-after.png`, `poc-minio-console-after.png`.

### Note format XL
Depuis ~2023, MinIO stocke les objets en format XL (erasure coding) :
chaque objet devient un fichier `<nom>.xl.meta` contenant données +
checksums + métadonnées. `find` montre ces fichiers, mais `aws s3 ls`
lit derrière le format et renvoie les noms/tailles logiques corrects.
Ne pas s'inquiéter de l'extension `.xl.meta`.

### Limite
Volume Docker local. Ne teste pas la réplication Longhorn 3 réplicas
sur 3 VM distinctes — sera vérifié sur cluster n2 le 20/11
(cf. section PostgreSQL + MinIO cluster).