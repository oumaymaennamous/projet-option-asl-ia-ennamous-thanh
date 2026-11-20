#!/usr/bin/env bash
set -euo pipefail

image=localhost/minio-j2:2025-10-15
archive="$HOME/mlops-j2/minio-j2.tar"
key="$HOME/.ssh/mlops-j2"
vms=(
  "k3s-server-1 192.168.122.53"
  "k3s-server-2 192.168.122.70"
  "k3s-server-3 192.168.122.152"
)

if [ ! -s "$archive" ]; then
  echo "Archive absente : $archive. Lancer d’abord build-minio.sh." >&2
  exit 1
fi
if [ ! -s "$key" ]; then
  echo "Clé SSH absente : $key." >&2
  exit 1
fi

for entry in "${vms[@]}"; do
  read -r vm ip <<<"$entry"
  remote_archive="minio-j2-import-$$.tar"
  echo "Import de l’image dans $vm ($ip)"
  ssh -o BatchMode=yes -i "$key" "ubuntu@$ip" true
  if ! ssh -o BatchMode=yes -i "$key" "ubuntu@$ip" \
    "test ! -e \"\$HOME/$remote_archive\""; then
    echo "Fichier temporaire déjà présent sur $vm : $remote_archive." >&2
    exit 1
  fi
  scp -o BatchMode=yes -i "$key" "$archive" "ubuntu@$ip:~/$remote_archive"
  ssh -o BatchMode=yes -i "$key" "ubuntu@$ip" \
    "sudo -n k3s ctr images import \"\$HOME/$remote_archive\" &&
     sudo -n k3s ctr images ls -q | grep -Fx '$image' &&
     rm -f -- \"\$HOME/$remote_archive\""
done
