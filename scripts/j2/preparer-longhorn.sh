#!/usr/bin/env bash
set -euo pipefail

# Depuis n2, préparer le moteur de données Longhorn V1 sur les trois VM.
for ip in 192.168.122.53 192.168.122.70 192.168.122.152; do
  ssh -i "$HOME/.ssh/mlops-j2" "ubuntu@$ip" '
    set -e
    hostname
    sudo -n apt-get update
    sudo -n apt-get install -y open-iscsi
    sudo -n systemctl enable --now iscsid
    systemctl is-active iscsid
    free -h
    df -Th /
  '
done
