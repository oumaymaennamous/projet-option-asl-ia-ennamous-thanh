#!/usr/bin/env bash
set -euo pipefail

vms=(
  "k3s-server-1 52:54:00:00:ef:17 192.168.122.53"
  "k3s-server-2 52:54:00:b1:6f:7f 192.168.122.70"
  "k3s-server-3 52:54:00:9a:d2:8e 192.168.122.152"
)
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
key="$HOME/.ssh/mlops-j2"
first=192.168.122.53
work_dir="$HOME/mlops-j2"

for command in sudo; do
  command -v "$command" >/dev/null || {
    echo "Commande requise absente : $command." >&2
    exit 1
  }
done

mkdir -p "$work_dir"
cd "$work_dir"

bash "$script_dir/preparer-hote.sh"

for command in virsh ssh scp ssh-keygen ssh-add awk grep; do
  command -v "$command" >/dev/null || {
    echo "Commande requise absente après préparation de l’hôte : $command." >&2
    exit 1
  }
done

for entry in "${vms[@]}"; do
  read -r vm mac _ <<<"$entry"
  if sudo virsh -c qemu:///system dominfo "$vm" >/dev/null 2>&1; then
    actual_mac=$(sudo virsh -c qemu:///system domiflist "$vm" |
      awk 'NR > 2 && $5 != "" { print tolower($5); exit }')
    if [ "$actual_mac" != "$mac" ]; then
      echo "La VM $vm existe avec la MAC $actual_mac (attendue : $mac)." >&2
      echo "Arrêt avant modification du réseau libvirt." >&2
      exit 1
    fi
  fi
done

bash "$script_dir/reserver-ip.sh"

for entry in "${vms[@]}"; do
  read -r vm mac ip <<<"$entry"
  if sudo virsh -c qemu:///system dominfo "$vm" >/dev/null 2>&1; then
    actual_mac=$(sudo virsh -c qemu:///system domiflist "$vm" |
      awk 'NR > 2 && $5 != "" { print tolower($5); exit }')
    if [ "$actual_mac" != "$mac" ]; then
      echo "La VM $vm existe avec la MAC $actual_mac (attendue : $mac)." >&2
      echo "Arrêt sans modifier la VM ni son disque." >&2
      exit 1
    fi
    state=$(sudo virsh -c qemu:///system domstate "$vm")
    if [ "$state" != "running" ]; then
      sudo virsh -c qemu:///system start "$vm"
    fi
  else
    bash "$script_dir/creer-vm.sh" "$vm"
  fi
done

if [ ! -s "$key" ]; then
  echo "Clé SSH absente après création des VM : $key." >&2
  exit 1
fi
if ! ssh-keygen -y -P "" -f "$key" >/dev/null 2>&1; then
  fingerprint=$(ssh-keygen -lf "$key.pub" | awk '{print $2}')
  if [ -z "$fingerprint" ] ||
    ! ssh-add -l 2>/dev/null | awk '{print $2}' | grep -Fxq "$fingerprint"; then
    echo "La clé SSH ne peut pas être déverrouillée sans interaction." >&2
    echo "Si elle est protégée par une phrase secrète, l’ajouter à ssh-agent avec ssh-add $key." >&2
    exit 1
  fi
fi

for entry in "${vms[@]}"; do
  read -r vm _ ip <<<"$entry"
  echo "Attente SSH : $vm ($ip)"
  ready=false
  for attempt in $(seq 1 90); do
    if ssh -o BatchMode=yes -o ConnectTimeout=3 -o StrictHostKeyChecking=accept-new \
      -i "$key" "ubuntu@$ip" true >/dev/null 2>&1; then
      ready=true
      break
    fi
    sleep 10
  done
  if [ "$ready" != true ]; then
    echo "SSH indisponible sur $vm ($ip) après 15 minutes." >&2
    exit 1
  fi
done

if ssh -o BatchMode=yes -i "$key" "ubuntu@$first" \
  'sudo -n k3s kubectl get nodes >/dev/null 2>&1'; then
  ready_nodes=$(ssh -o BatchMode=yes -i "$key" "ubuntu@$first" \
    "sudo -n k3s kubectl get nodes --no-headers | awk '\$2 == \"Ready\" { n++ } END { print n+0 }'")
  if [ "$ready_nodes" != 3 ]; then
    echo "Le cluster K3s répond mais n’a que $ready_nodes nœud(s) Ready ; arrêt sans réinstallation." >&2
    exit 1
  fi
  echo "Cluster K3s déjà opérationnel ; installation ignorée."
else
  for entry in "${vms[@]}"; do
    read -r vm _ ip <<<"$entry"
    if ssh -o BatchMode=yes -i "$key" "ubuntu@$ip" \
      '[ -x /usr/local/bin/k3s ] || systemctl list-unit-files k3s.service --no-legend | grep -q "^k3s.service"'; then
      echo "K3s est installé sur $vm mais le cluster n’est pas vérifiable ; arrêt sans réinstallation." >&2
      exit 1
    fi
  done
  bash "$script_dir/installer-k3s.sh"
fi

bash "$script_dir/preparer-longhorn.sh"
bash "$script_dir/installer-longhorn.sh"

image_nodes=0
for entry in "${vms[@]}"; do
  read -r vm _ ip <<<"$entry"
  if ssh -o BatchMode=yes -i "$key" "ubuntu@$ip" \
    "sudo -n k3s ctr images ls -q | grep -Fx 'localhost/minio-j2:2025-10-15' >/dev/null"; then
    image_nodes=$((image_nodes + 1))
  fi
done
if [ "$image_nodes" -eq 0 ]; then
  bash "$script_dir/build-minio.sh"
  bash "$script_dir/import-minio.sh"
elif [ "$image_nodes" -ne 3 ]; then
  echo "Image MinIO présente sur $image_nodes/3 nœuds. Arrêt pour éviter un déploiement incohérent." >&2
  exit 1
else
  echo "Image MinIO présente sur les trois nœuds ; construction/import ignorés."
fi

bash "$script_dir/deployer-services.sh"
echo "Socle J2 déployé. Le test de persistance avec redémarrage des pods reste une étape séparée."
