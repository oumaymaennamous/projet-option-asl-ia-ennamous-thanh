#!/usr/bin/env bash
set -euo pipefail

# À lancer sur n2, avec un répertoire de travail dédié.
case "${1:-}" in
  k3s-server-1|k3s-server-2|k3s-server-3) vm=$1 ;;
  *) echo "Usage : bash $0 k3s-server-{1,2,3}" >&2; exit 1 ;;
esac

image=noble-server-cloudimg-amd64.img
disque="/var/lib/libvirt/images/$vm.qcow2"
cle="$HOME/.ssh/mlops-j2"
config="$PWD/$vm-user-data.yaml"

sudo -v
if sudo virsh -c qemu:///system dominfo "$vm" >/dev/null 2>&1 ||
   sudo test -e "$disque"; then
  echo "La VM $vm ou son disque existe déjà." >&2
  exit 1
fi

if [ ! -s "$image" ]; then
  wget -O "$image.part" "https://cloud-images.ubuntu.com/noble/current/$image"
  mv "$image.part" "$image"
fi

mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
if [ ! -f "$cle" ]; then
  ssh-keygen -t ed25519 -f "$cle"
fi

cle_publique=$(cat "$cle.pub")
printf '%s\n' \
  '#cloud-config' \
  "hostname: $vm" \
  'users: [default]' \
  'ssh_pwauth: false' \
  'ssh_authorized_keys:' \
  "  - $cle_publique" > "$config"

sudo qemu-img convert -O qcow2 "$image" "$disque"
sudo qemu-img resize "$disque" 24G
sudo virt-install --connect qemu:///system \
  --name "$vm" --memory 3072 --vcpus 2 \
  --osinfo generic --import \
  --disk "path=$disque,format=qcow2,bus=virtio" \
  --network network=default,model=virtio \
  --cloud-init "user-data=$config" \
  --noautoconsole
