# J2 — Déployer MinIO sur le cluster k3s de l’école

Le 18 novembre 2026, MinIO a été déployé sur le cluster de l’école. Le bucket privé `mlflow-artifacts` a été créé via l’API S3. Le fichier `preuve-j2.txt` a été relu après la suppression et la recréation du pod MinIO, puis retrouvé dans la console web.

Le déploiement peut être exécuté par phases avec les scripts du dépôt, ou avec l’orchestrateur global [`reconstruire-j2.sh`](reconstruire-j2.sh). Le manifeste du serveur est conservé dans [`minio.yaml`](minio.yaml), le Containerfile dans [`minio.Containerfile`](minio.Containerfile), et le client de test dans [`test-s3.yaml`](test-s3.yaml).

Cette procédure suppose un cluster déjà installé et la StorageClass `longhorn-3copies` disponible. Le script global crée ou réutilise les Secrets de façon prudente ; il s’arrête si un Secret manque alors que des données applicatives existent. Il ne supprime pas de PVC. La reconstruction doit encore être validée sur une cible propre.

[`minio.yaml`](minio.yaml) déploie le serveur MinIO ; [`test-s3.yaml`](test-s3.yaml) définit le pod client `test-s3-j2`.

## 1. Vérifier les prérequis

| Machine | Adresse | Rôle |
| --- | --- | --- |
| `n2` | `172.19.3.42` | Hôte KVM/libvirt, construction Podman et accès SSH |
| `k3s-server-1` | `192.168.122.53` | Premier serveur k3s |
| `k3s-server-2` | `192.168.122.70` | Deuxième serveur k3s |
| `k3s-server-3` | `192.168.122.152` | Troisième serveur k3s |

La clé `~/.ssh/mlops-j2` est sur `n2`. Les VM doivent être démarrées, k3s opérationnel et la StorageClass `longhorn-3copies` disponible. PostgreSQL est déjà en place dans `mlops`.

Depuis `ops@n2`, si les trois VM sont arrêtées, les démarrer.

```bash
for vm in k3s-server-{1,2,3}; do
  sudo virsh -c qemu:///system start "$vm"
done
```

```bash
ssh -i ~/.ssh/mlops-j2 ubuntu@192.168.122.53 '
  sudo k3s kubectl get nodes -o wide &&
  sudo k3s kubectl get storageclass longhorn-3copies &&
  sudo k3s kubectl -n mlops get pod postgres-0
'
```

## 1 bis. Prérequis réseau : résolution DNS (obligatoire)

Le résolveur DNS de l'école (`172.19.0.254`) ne résout pas `ghcr.io` ni `pypi.org` (constaté le 20/11/2026 ; `1.1.1.1` répond correctement). Sans contournement, ni le pull des images externes ni `pip install` ne fonctionnent. Le réglage est **temporaire** : il disparaît au redémarrage d'une VM.

```bash
for ip in 192.168.122.53 192.168.122.70 192.168.122.152; do
  ssh -i ~/.ssh/mlops-j2 "ubuntu@$ip" '
    sudo resolvectl dns ens3 1.1.1.1 &&
    sudo resolvectl flush-caches &&
    getent ahostsv4 ghcr.io | head -1 &&
    getent ahostsv4 pypi.org | head -1
  '
done
ssh -i ~/.ssh/mlops-j2 ubuntu@192.168.122.53 \
  'sudo k3s kubectl -n kube-system rollout restart deployment/coredns'
```

Chaque VM doit afficher une adresse pour les deux noms. Solution durable à implémenter avant J5 : DNS fixe dans cloud-init, ou `server=1.1.1.1` dans le dnsmasq du réseau libvirt `default`.

## 2. Construire l’image locale sur n2

Podman compile MinIO depuis le tag source choisi. L’archive permet d’importer la même image dans le containerd de chaque VM. Ainsi, k3s peut démarrer MinIO sur chacun des trois nœuds à partir de son cache local.

```bash
bash scripts/j2/build-minio.sh
```

Le script produit `~/mlops-j2/minio-j2.tar`, vérifie la version du binaire et affiche l’empreinte SHA-256 de l’archive. Le binaire affiche `DEVELOPMENT.GOGET` : le tag source fixe la version demandée, mais le commit n’est pas vérifié. Les images de base `golang:1.24-alpine` et `alpine:3.23` sont des tags flottants, non épinglés par digest ; cette limite reste à traiter avant J5.

## 3. Importer l’image sur les trois VM

Depuis `n2`, importer la même archive dans le containerd de chaque VM :

```bash
bash scripts/j2/import-minio.sh
```

## 4. Créer les Secrets et déployer PostgreSQL/MinIO

```bash
bash scripts/j2/deployer-services.sh
```

Le script vérifie la StorageClass et la présence de l’image MinIO sur les trois nœuds, crée le namespace si nécessaire, crée les Secrets seulement s’ils manquent et applique les manifestes PostgreSQL et MinIO. Le mot de passe MinIO est saisi sans affichage. Les Secrets existants sont conservés.

## 5. Vérifier la persistance

```bash
bash scripts/j2/verifier-persistance.sh --confirm-interruption
```

Le script demande une confirmation, crée une table et un objet S3 de test uniques, supprime uniquement les pods `postgres-0` et `minio-0`, attend leur recréation, puis relit les données. Il ne supprime pas les PVC ni les données de test. Le pod client installe `boto3` depuis PyPI, donc le DNS et l’accès réseau requis doivent fonctionner.

```text
MinIO J2 : donnees conservees
```

## 6. Ouvrir la console MinIO depuis Windows

Depuis `ops@n2`, ouvrir le premier relais SSH vers la VM et lancer le port-forward Kubernetes vers le pod. Laisser ce terminal ouvert.

```bash
ssh -o ExitOnForwardFailure=yes -i ~/.ssh/mlops-j2 \
  -L 127.0.0.1:19001:127.0.0.1:9001 ubuntu@192.168.122.53 \
  'sudo -n k3s kubectl -n mlops port-forward --address 127.0.0.1 pod/minio-0 9001:9001'
```

Sur Windows, ouvrir un autre terminal PowerShell et établir le deuxième relais. Laisser ce terminal ouvert aussi.

```powershell
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:9001:127.0.0.1:19001 ops@172.19.3.42
```

Ouvrir [la console MinIO](http://127.0.0.1:9001), saisir les identifiants du Secret et sélectionner le bucket `mlflow-artifacts`. L’objet historique s’appelle `preuve-j2.txt` ; le script de persistance ajoute un objet unique sous `preuves/`. La capture existante montre le bucket privé et l’objet historique de 29 octets. En cas de recréation du pod après l’ouverture de la console, relancer le port-forward côté `n2`.

| Accès | Adresse | Usage |
| --- | --- | --- |
| API S3 interne | `http://minio:9000` depuis le namespace `mlops` | Clients S3 et, à l’étape suivante, serveur MLflow |
| Console web | `http://127.0.0.1:9001` depuis Windows | Consultation du bucket et de ses objets |

## Résultat et suite du projet

La relecture du fichier prouve la persistance lors de la recréation du pod MinIO. Le prochain jalon consiste à configurer MLflow pour enregistrer ses métadonnées dans PostgreSQL et ses artefacts dans `s3://mlflow-artifacts`.
