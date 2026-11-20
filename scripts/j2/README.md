# Reproduire le socle J2 jusqu’à PostgreSQL

[Journal et résultats de la séance du 10 novembre](../../docs/journal/2026-11-10.md). Les scripts, manifestes et commandes de reproduction sont regroupés ici.

## Reconstruction automatisée

Sur l’hôte Ubuntu `n2`, depuis la racine du dépôt cloné :

```bash
bash scripts/j2/reconstruire-j2.sh
```

Si la clé `~/.ssh/mlops-j2` existante est protégée par une phrase secrète, la charger d’abord dans `ssh-agent` avec `ssh-add ~/.ssh/mlops-j2`. Une nouvelle clé créée par le script n’a pas de phrase secrète.

Le script prépare les paquets de l’hôte, réserve les adresses, crée ou démarre les VM, installe K3s et Longhorn, construit/import MinIO si son image manque sur tous les nœuds, puis applique PostgreSQL et MinIO. Il crée les Secrets seulement s’ils manquent et refuse de générer un nouveau Secret si des données applicatives existent déjà.

Le script ne supprime pas de VM, de PVC ni de données. Il s’arrête si les VM existantes ont des MAC différentes, si K3s est partiellement installé ou si l’image MinIO n’est présente que sur une partie des nœuds. **La procédure doit encore être exécutée sur une cible propre pour valider la reconstruction J2.** Sur un cluster déjà en service, l’application de manifestes peut déclencher un redémarrage si leur spécification a changé ; ne pas relancer sans vérifier l’état du cluster.

Pour tester la persistance en redémarrant les pods PostgreSQL et MinIO (interruption brève, PVC conservés), utiliser ensuite la [procédure de vérification](verifier-persistance.sh) ; elle exige l’option `--confirm-interruption` et une confirmation interactive.

Les étapes détaillées ci-dessous restent disponibles pour diagnostiquer ou rejouer une phase précise. La procédure MinIO est également décrite dans [déployer MinIO sur le cluster](minio-j2.md).

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
sudo apt install cloud-image-utils qemu-kvm libvirt-daemon-system libvirt-clients \
  qemu-utils virtinst openssh-client podman wget
sudo virsh -c qemu:///system list --all
sudo virsh -c qemu:///system net-list --all
```

Depuis la racine du dépôt cloné sur `n2`, lance les commandes suivantes. Le dossier de travail séparé reçoit l’image Cloud et les fichiers cloud-init générés.

```bash
scripts_j2="$PWD/scripts/j2"
mkdir -p ~/mlops-j2
cd ~/mlops-j2

bash "$scripts_j2/reserver-ip.sh"
bash "$scripts_j2/creer-vm.sh" k3s-server-1
sudo virsh -c qemu:///system domifaddr k3s-server-1 --source lease
ssh -i ~/.ssh/mlops-j2 ubuntu@192.168.122.53 'hostname; df -h /'

bash "$scripts_j2/creer-vm.sh" k3s-server-2
bash "$scripts_j2/creer-vm.sh" k3s-server-3
sudo virsh -c qemu:///system list --all
sudo virsh -c qemu:///system net-dhcp-leases default
```

`creer-vm.sh` assigne les MAC correspondant aux réservations. Vérifier les trois baux et les accès SSH avant l’installation groupée.

```bash
ssh -i ~/.ssh/mlops-j2 ubuntu@192.168.122.70 hostname
ssh -i ~/.ssh/mlops-j2 ubuntu@192.168.122.152 hostname
bash "$scripts_j2/installer-k3s.sh"
bash "$scripts_j2/preparer-longhorn.sh"
bash "$scripts_j2/installer-longhorn.sh"
```

Le premier serveur a utilisé le canal stable pendant la séance. Le script d’installation fixe sur les trois VM la version K3s obtenue ce jour-là. En revanche, l’image Ubuntu provient de l’URL mobile `noble/current` et n’est pas épinglée par empreinte ; une reconstruction identique bit à bit n’est donc pas garantie. Si son téléchargement échoue sur la résolution DNS, vérifier `getent ahostsv4 cloud-images.ubuntu.com` et `resolvectl status enp0s31f6`.

## 2. Depuis la première VM K3s

Copier les deux manifestes sur la première VM et s’y connecter.

```bash
scp -i ~/.ssh/mlops-j2 "$scripts_j2/test-longhorn.yaml" "$scripts_j2/postgres.yaml" ubuntu@192.168.122.53:~/
ssh -i ~/.ssh/mlops-j2 ubuntu@192.168.122.53
```

Vérifier que Longhorn et sa StorageClass sont prêts. L’installation se lance depuis `n2` avec `installer-longhorn.sh` ; ne pas relancer les commandes `apply` si ce script vient de s’exécuter.

```bash
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

Créer le namespace et le secret uniquement lors de l’installation initiale. La commande génère le mot de passe à l’exécution, sans l’écrire dans le manifeste. Ces ressources ne sont pas créées par `postgres.yaml`; sur un cluster existant, ne pas recréer le Secret sans avoir vérifié son usage et conservé le mot de passe correspondant.

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
