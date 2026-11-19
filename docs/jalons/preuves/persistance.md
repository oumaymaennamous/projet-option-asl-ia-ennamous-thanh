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