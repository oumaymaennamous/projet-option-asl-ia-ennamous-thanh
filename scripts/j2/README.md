# Reproduire le socle J2 jusqu’à PostgreSQL

[Journal et résultats de la séance du 10 novembre](../../docs/journal/2026-11-10.md). Les scripts regroupent les commandes de la séance. Les adresses et MAC correspondent à `n2` et sont à adapter sur une autre cible. La procédure de création et d’installation vise des VM neuves. Pour consulter le cluster existant, utiliser les commandes de vérification.

## 1. Sur l’hôte physique Ubuntu

```bash
lscpu | grep -Ei 'model name|cpu\(s\)|virtuali'
ls -l /dev/kvm
free -h
lsblk -o NAME,SIZE,TYPE,MOUNTPOINTS
df -h /
ip -br link
ip -br addr
ip route

sudo apt update
sudo apt install qemu-kvm libvirt-daemon-system libvirt-clients virtinst
sudo virsh -c qemu:///system list --all
sudo virsh -c qemu:///system net-list --all
```

Depuis la racine du dépôt cloné sur `n2`, lance les commandes suivantes. Le dossier de travail séparé reçoit l’image Cloud et les fichiers cloud-init générés.

```bash
scripts_j2="$PWD/scripts/j2"
mkdir -p ~/mlops-j2
cd ~/mlops-j2

bash "$scripts_j2/creer-vm.sh" k3s-server-1
sudo virsh -c qemu:///system domifaddr k3s-server-1 --source lease
ssh -i ~/.ssh/mlops-j2 ubuntu@192.168.122.53 'hostname; df -h /'

bash "$scripts_j2/creer-vm.sh" k3s-server-2
bash "$scripts_j2/creer-vm.sh" k3s-server-3
sudo virsh -c qemu:///system list --all
sudo virsh -c qemu:///system net-dhcp-leases default
```

Attendre les trois baux DHCP. Comparer les MAC et les IP à celles de `reserver-ip.sh` et des scripts suivants. Le script de réservations est à lancer une seule fois pour les baux de cette cible. Les accès SSH initiaux doivent fonctionner sur les trois VM avant d’exécuter l’installation groupée.

```bash
bash "$scripts_j2/reserver-ip.sh"
ssh -i ~/.ssh/mlops-j2 ubuntu@192.168.122.70 hostname
ssh -i ~/.ssh/mlops-j2 ubuntu@192.168.122.152 hostname
bash "$scripts_j2/installer-k3s.sh"
bash "$scripts_j2/preparer-longhorn.sh"
```

Le premier serveur a utilisé le canal stable pendant la séance. Le script de reproduction fixe sur les trois VM la version obtenue ce jour-là. Si le téléchargement de l’image Ubuntu échoue sur la résolution DNS, vérifier `getent ahostsv4 cloud-images.ubuntu.com` et `resolvectl status enp0s31f6`.

## 2. Depuis la première VM K3s

Copier les deux manifestes sur la première VM et s’y connecter.

```bash
scp -i ~/.ssh/mlops-j2 "$scripts_j2/test-longhorn.yaml" "$scripts_j2/postgres.yaml" ubuntu@192.168.122.53:~/
ssh -i ~/.ssh/mlops-j2 ubuntu@192.168.122.53
```

Installer Longhorn et attendre le démarrage.

```bash
curl -fsSL https://raw.githubusercontent.com/longhorn/longhorn/v1.13.0/deploy/longhorn.yaml \
  -o longhorn-v1.13.0.yaml &&
sudo k3s kubectl apply -f longhorn-v1.13.0.yaml &&
sudo k3s kubectl -n longhorn-system rollout status daemonset/longhorn-manager --timeout=5m &&
sudo k3s kubectl -n longhorn-system rollout status deployment/longhorn-driver-deployer --timeout=5m

sudo k3s kubectl -n longhorn-system get pods -o wide
sudo k3s kubectl -n longhorn-system get nodes.longhorn.io
sudo k3s kubectl get storageclass
```

Exécuter le test de stockage. La suppression concerne uniquement le pod `test-longhorn`, dont le PVC reste en place.

```bash
sudo k3s kubectl apply -f test-longhorn.yaml &&
sudo k3s kubectl wait --for=condition=Ready pod/test-longhorn --timeout=5m &&
sudo k3s kubectl exec test-longhorn -- sh -c 'echo "Test J2 : donnees conservees" > /data/preuve.txt' &&
sudo k3s kubectl delete pod test-longhorn &&
sudo k3s kubectl apply -f test-longhorn.yaml &&
sudo k3s kubectl wait --for=condition=Ready pod/test-longhorn --timeout=5m &&
sudo k3s kubectl exec test-longhorn -- cat /data/preuve.txt

sudo k3s kubectl get pvc test-longhorn
sudo k3s kubectl -n longhorn-system get volumes.longhorn.io
sudo k3s kubectl -n longhorn-system get replicas.longhorn.io \
  -o 'custom-columns=VOLUME:.spec.volumeName,NOEUD:.spec.nodeID,ETAT:.status.currentState'
```

Créer le namespace et le secret uniquement lors de l’installation initiale. La commande génère le mot de passe à l’exécution, sans l’écrire dans le manifeste.

```bash
sudo k3s kubectl create namespace mlops
(
  set -o pipefail
  openssl rand -hex 24 | tr -d '\n' |
    sudo k3s kubectl -n mlops create secret generic postgres-auth --from-file=password=/dev/stdin
)

sudo k3s kubectl apply -f postgres.yaml &&
sudo k3s kubectl -n mlops rollout status statefulset/postgres --timeout=5m
```

Une fois PostgreSQL prêt, tester la persistance sur le cluster de labo. La suppression du pod PostgreSQL entraîne une interruption de cette instance.

```bash
sudo k3s kubectl -n mlops exec postgres-0 -- \
  psql -U mlflow -d mlflow -v ON_ERROR_STOP=1 \
  -c "CREATE TABLE IF NOT EXISTS preuve_j2 (message text); INSERT INTO preuve_j2 VALUES ('PostgreSQL : donnees conservees');" &&
sudo k3s kubectl -n mlops delete pod postgres-0 &&
sudo k3s kubectl -n mlops rollout status statefulset/postgres --timeout=5m &&
sudo k3s kubectl -n mlops exec postgres-0 -- \
  psql -U mlflow -d mlflow -c 'SELECT * FROM preuve_j2;'

sudo k3s kubectl -n mlops get pod,pvc
```

## 3. Headlamp sur un poste Windows autorisé

Le poste doit pouvoir joindre `n2` sur le port SSH. Relever l’IPv4 de `n2` avec `ip -br addr` sur l’hôte, puis la saisir dans le premier PowerShell et dans le deuxième.

```powershell
$n2 = Read-Host "Adresse IPv4 de n2"
Test-NetConnection $n2 -Port 22
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:16443:192.168.122.53:6443 "ops@$n2"
```

Garder ce terminal ouvert. Depuis une session sur `n2`, préparer une copie temporaire du kubeconfig administrateur.

```bash
(
  umask 077
  ssh -i ~/.ssh/mlops-j2 ubuntu@192.168.122.53 \
    'sudo -n cat /etc/rancher/k3s/k3s.yaml' > ~/mlops-j2/k3s-ecole.yaml
)
```

Dans un deuxième PowerShell, copier le fichier dans le profil Windows et modifier l’adresse de l’API pour utiliser le tunnel.

```powershell
$fichier = "$env:USERPROFILE\.kube\k3s-ecole.yaml"
New-Item -ItemType Directory -Force "$env:USERPROFILE\.kube" | Out-Null
$n2 = Read-Host "Adresse IPv4 de n2"
scp "ops@${n2}:mlops-j2/k3s-ecole.yaml" "$fichier"
if ($LASTEXITCODE -eq 0) {
    (Get-Content -Raw $fichier).Replace('https://127.0.0.1:6443', 'https://127.0.0.1:16443') |
        Set-Content -Encoding ascii $fichier
}
```

Après une copie réussie, supprimer la copie temporaire de `n2` avec `rm ~/mlops-j2/k3s-ecole.yaml`. Fermer Headlamp s’il est déjà ouvert. Récupérer le chemin réel de son exécutable dans les propriétés du raccourci Windows et lancer l’application avec ce kubeconfig.

```powershell
$headlamp = (Read-Host "Colle le chemin de Headlamp.exe").Trim('"')
& $headlamp "$fichier"
```

Dans **Nodes**, vérifier les trois nœuds. Dans **Pods**, sélectionner `longhorn-system` pour Longhorn ou `mlops` pour PostgreSQL. Le kubeconfig donne des droits administrateur. Chaque membre doit utiliser un accès autorisé et conserver ses fichiers d’accès hors Git.
