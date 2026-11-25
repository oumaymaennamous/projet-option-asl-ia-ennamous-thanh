# J2 — Déployer MinIO sur le cluster k3s de l’école

Le 18 novembre 2026, MinIO a été déployé sur le cluster de l’école. Le bucket privé `mlflow-artifacts` a été créé via l’API S3. Le fichier `preuve-j2.txt` a été relu après la suppression et la recréation du pod MinIO, puis retrouvé dans la console web.

Ce guide reprend les étapes utiles à la reproduction. Le manifeste ci-dessous est une version consolidée avec la console activée dès le départ.

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

**Solution durable testée sur `k3s-server-2` (25/11/2026).** Fichier `/etc/netplan/60-dns.yaml` (ne pas modifier `50-cloud-init.yaml`, que cloud-init peut régénérer) :

```yaml
network:
  version: 2
  ethernets:
    ens3:
      dhcp4-overrides:
        use-dns: false
      dhcp6-overrides:
        use-dns: false
      nameservers:
        addresses: [1.1.1.1]
```

Les deux blocs `*-overrides` sont obligatoires : `networkd` refuse une valeur différente de `use-dns` entre IPv4 et IPv6. Procédure : `sudo chmod 600 /etc/netplan/60-dns.yaml`, `sudo netplan generate`, puis `sudo netplan try`. Validé après redémarrage de la seule `k3s-server-2` ; non appliqué à `k3s-server-1` et `k3s-server-3`. Vérifier avant de redémarrer un nœud que nœuds `Ready` et volumes Longhorn `healthy`.

## 2. Construire l’image locale sur n2

Podman compile MinIO depuis le tag source choisi. L’archive permet d’importer la même image dans le containerd de chaque VM. Ainsi, k3s peut démarrer MinIO sur chacun des trois nœuds à partir de son cache local.

```bash
mkdir -p ~/mlops-j2/minio-build
cd ~/mlops-j2/minio-build

cat > Containerfile <<'EOF'
FROM docker.io/library/golang:1.24-alpine AS build
ENV CGO_ENABLED=0 GOMAXPROCS=2
RUN go install -p=2 github.com/minio/minio@RELEASE.2025-10-15T17-29-55Z

FROM docker.io/library/alpine:3.23
COPY --from=build /go/bin/minio /usr/local/bin/minio
ENTRYPOINT ["/usr/local/bin/minio"]
EOF

image=localhost/minio-j2:2025-10-15
sudo podman build -t "$image" . &&
sudo podman run --rm "$image" --version &&
sudo podman save --format docker-archive -o minio-j2.tar "$image" &&
ls -lh minio-j2.tar
```

L’archive produite pendant le test faisait environ 153 Mo. Le binaire affiche DEVELOPMENT.GOGET : le tag passé à go install fixe la version source, mais le commit n’est pas vérifié et les images de base golang:1.24-alpine et alpine:3.23 sont des tags flottants (non épinglés par digest). Limite connue pour J5.

## 3. Importer l’image sur les trois VM

Toujours depuis `n2`, dans `~/mlops-j2/minio-build`.

```bash
(
  set -euo pipefail
  for ip in 192.168.122.53 192.168.122.70 192.168.122.152; do
    scp -i ~/.ssh/mlops-j2 minio-j2.tar "ubuntu@$ip:~/minio-j2.tar"
    ssh -i ~/.ssh/mlops-j2 "ubuntu@$ip" '
      hostname &&
      sudo -n k3s ctr images import "$HOME/minio-j2.tar" &&
      sudo -n k3s ctr images ls -q | grep -Fx "localhost/minio-j2:2025-10-15"
    '
  done
)
```

## 4. Créer le secret et déployer MinIO

Connecte-toi à `k3s-server-1` depuis `n2`. Toutes les commandes Kubernetes jusqu’à la section console peuvent ensuite être exécutées depuis cette VM.

```bash
ssh -i ~/.ssh/mlops-j2 ubuntu@192.168.122.53
```

Sur une nouvelle installation, créer le Secret avec un mot de passe fort saisi sans affichage. Si `minio-secret` existe déjà, réutiliser ses identifiants.

```bash
read -rsp 'Mot de passe MinIO (au moins 8 caractères) : ' MINIO_PASSWORD
echo
if [ "${#MINIO_PASSWORD}" -ge 8 ]; then
  sudo -v &&
  printf 'MINIO_ROOT_USER=mlops-s3\nMINIO_ROOT_PASSWORD=%s\n' "$MINIO_PASSWORD" |
    sudo -n k3s kubectl -n mlops create secret generic minio-secret --from-env-file=/dev/stdin
else
  echo 'Le mot de passe doit contenir au moins 8 caractères.'
fi
unset MINIO_PASSWORD
```

```bash
cat > minio.yaml <<'EOF'
apiVersion: v1
kind: Service
metadata:
  name: minio
  namespace: mlops
spec:
  selector:
    app: minio
  ports:
    - name: s3
      port: 9000
      targetPort: s3
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: minio
  namespace: mlops
spec:
  serviceName: minio
  replicas: 1
  selector:
    matchLabels:
      app: minio
  template:
    metadata:
      labels:
        app: minio
    spec:
      containers:
        - name: minio
          image: localhost/minio-j2:2025-10-15
          imagePullPolicy: Never
          args: ["server", "/data", "--console-address", ":9001"]
          envFrom:
            - secretRef:
                name: minio-secret
          ports:
            - name: s3
              containerPort: 9000
            - name: console
              containerPort: 9001
          readinessProbe:
            httpGet:
              path: /minio/health/ready
              port: s3
          livenessProbe:
            httpGet:
              path: /minio/health/live
              port: s3
            initialDelaySeconds: 15
            periodSeconds: 20
          resources:
            requests: { cpu: 100m, memory: 256Mi }
            limits: { memory: 512Mi }
          volumeMounts:
            - name: data
              mountPath: /data
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: longhorn-3copies
        resources:
          requests:
            storage: 2Gi
EOF

sudo k3s kubectl apply -f minio.yaml &&
sudo k3s kubectl -n mlops rollout status statefulset/minio --timeout=5m &&
sudo k3s kubectl -n mlops get pod/minio-0 pvc/data-minio-0 svc/minio
```

Le résultat attendu est `minio-0` en `Running` et le PVC `data-minio-0` en `Bound`. Les objets S3 sont écrits dans le volume Longhorn monté sur `/data`. Le StatefulSet gère une instance MinIO, tandis que Longhorn gère les trois répliques du volume.

## 5. Créer le bucket et écrire un objet

Le pod de test utilise Python et `boto3`. Le nœud doit pouvoir récupérer l’image Python et le pod doit pouvoir résoudre et joindre PyPI pour installer `boto3`.

Le pod client vit 1 h (sleep 3600) puis passe en Completed. Les étapes 5 et 6 recréent le pod, donc rien à faire ; pour rejouer seulement l’étape 6 plus d’une heure après, relancer d’abord l’étape 5.

### Pod client et script de test

Le pod est placé sur `k3s-server-2`, comme pendant le test sur le cluster de l’école.

```bash
cat > test-s3-j2.yaml <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: test-s3-j2
  namespace: mlops
spec:
  restartPolicy: Never
  nodeSelector:
    kubernetes.io/hostname: k3s-server-2
  containers:
    - name: client
      image: docker.io/library/python:3.12-slim
      imagePullPolicy: IfNotPresent
      envFrom:
        - secretRef:
            name: minio-secret
      command: ["sh", "-ec"]
      args:
        - |
          pip install --quiet --disable-pip-version-check boto3
          touch /tmp/client-ready
          sleep 3600
      readinessProbe:
        exec:
          command: ["test", "-f", "/tmp/client-ready"]
EOF

sudo k3s kubectl -n mlops delete pod test-s3-j2 --ignore-not-found &&
sudo k3s kubectl apply -f test-s3-j2.yaml &&
sudo k3s kubectl -n mlops wait --for=condition=Ready pod/test-s3-j2 --timeout=3m
```

Créer un script avec deux actions. `ecrire` crée le bucket s’il manque et écrit l’objet. `lire` vérifie les octets de l’objet existant après la recréation de MinIO.

```bash
cat > verifier-s3.py <<'PY'
import os
import sys

import boto3
from botocore.config import Config

bucket = "mlflow-artifacts"
cle = "preuve-j2.txt"
attendu = b"MinIO J2 : donnees conservees"

s3 = boto3.client(
    "s3",
    endpoint_url="http://minio:9000",
    aws_access_key_id=os.environ["MINIO_ROOT_USER"],
    aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],
    region_name="us-east-1",
    config=Config(s3={"addressing_style": "path"}),
)

action = sys.argv[1]
if action == "ecrire":
    buckets = {item["Name"] for item in s3.list_buckets()["Buckets"]}
    if bucket not in buckets:
        s3.create_bucket(Bucket=bucket)
    s3.put_object(Bucket=bucket, Key=cle, Body=attendu)
    print(f"Objet ecrit : {bucket}/{cle}")
elif action == "lire":
    objet = s3.get_object(Bucket=bucket, Key=cle)
    contenu = objet["Body"].read()
    if contenu != attendu:
        raise SystemExit("Le contenu relu diffère du contenu écrit.")
    print(contenu.decode())
else:
    raise SystemExit("Action attendue : ecrire ou lire.")
PY

sudo k3s kubectl -n mlops exec -i test-s3-j2 -- python - ecrire < verifier-s3.py
```

## 6. Vérifier la persistance avec une recréation du pod

Cette commande interrompt brièvement MinIO. Le StatefulSet recrée `minio-0` et lui rattache son PVC. La dernière commande relit l’objet sans le réécrire.

```bash
sudo k3s kubectl -n mlops delete pod minio-0 &&
sudo k3s kubectl -n mlops rollout status statefulset/minio --timeout=5m &&
sudo k3s kubectl -n mlops exec -i test-s3-j2 -- python - lire < verifier-s3.py
```

Résultat attendu.

```text
MinIO J2 : donnees conservees
```

Une fois le test terminé, supprimer le pod client.

```bash
sudo k3s kubectl -n mlops delete pod test-s3-j2
```

## 7. Ouvrir la console MinIO depuis Windows

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

Ouvrir [la console MinIO](http://127.0.0.1:9001), saisir les identifiants du Secret, sélectionner le bucket `mlflow-artifacts` puis `preuve-j2.txt`. La capture de la session montre le bucket privé et l’objet de 29 octets. En cas de recréation du pod après l’ouverture de la console, relancer le port-forward côté `n2`.

| Accès | Adresse | Usage |
| --- | --- | --- |
| API S3 interne | `http://minio:9000` depuis le namespace `mlops` | Clients S3 et, à l’étape suivante, serveur MLflow |
| Console web | `http://127.0.0.1:9001` depuis Windows | Consultation du bucket et de ses objets |

## Résultat et suite du projet

La relecture du fichier prouve la persistance lors de la recréation du pod MinIO. Le prochain jalon consiste à configurer MLflow pour enregistrer ses métadonnées dans PostgreSQL et ses artefacts dans `s3://mlflow-artifacts`.
