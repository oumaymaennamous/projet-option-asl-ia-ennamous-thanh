#!/usr/bin/env bash
set -euo pipefail

# Depuis n2, après avoir vérifié les trois connexions SSH et les réservations.
cle="$HOME/.ssh/mlops-j2"
premier=192.168.122.53
version=v1.37.2+k3s1

ssh -i "$cle" "ubuntu@$premier" \
  "curl -fsSL https://get.k3s.io -o install-k3s.sh &&
   sudo -n env INSTALL_K3S_VERSION='$version' \
     sh install-k3s.sh server --cluster-init --node-ip '$premier' &&
   sudo -n systemctl is-active k3s"

for ip in 192.168.122.70 192.168.122.152; do
  echo "Rattachement de la VM $ip"
  ssh -i "$cle" "ubuntu@$premier" \
    'sudo -n cat /var/lib/rancher/k3s/server/token' |
    ssh -i "$cle" "ubuntu@$ip" \
      "sudo -n mkdir -p /etc/rancher/k3s &&
       sudo -n sh -c 'umask 077; cat > /etc/rancher/k3s/join-token'"
  ssh -i "$cle" "ubuntu@$ip" \
    "curl -fsSL https://get.k3s.io -o install-k3s.sh &&
     sudo -n env INSTALL_K3S_VERSION='$version' \
       sh install-k3s.sh server --server 'https://$premier:6443' \
       --token-file /etc/rancher/k3s/join-token --node-ip '$ip' &&
     sudo -n systemctl is-active k3s"
done

ssh -i "$cle" "ubuntu@$premier" 'sudo -n k3s kubectl get nodes -o wide'
