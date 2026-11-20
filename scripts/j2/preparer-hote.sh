#!/usr/bin/env bash
set -euo pipefail

if [ ! -r /etc/os-release ] || ! grep -q '^ID=ubuntu$' /etc/os-release; then
  echo "Ce script cible Ubuntu sur l’hôte KVM." >&2
  exit 1
fi

sudo -v
sudo apt-get update
sudo apt-get install -y \
  cloud-image-utils \
  libvirt-clients \
  libvirt-daemon-system \
  openssh-client \
  podman \
  qemu-kvm \
  qemu-utils \
  virtinst \
  wget

if [ ! -e /dev/kvm ]; then
  echo "/dev/kvm absent ; vérifier la virtualisation matérielle sur l’hôte." >&2
  exit 1
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
virsh_cmd=(sudo virsh -c qemu:///system)
if ! "${virsh_cmd[@]}" net-info default >/dev/null 2>&1; then
  "${virsh_cmd[@]}" net-define "$script_dir/libvirt-default-network.xml"
fi

network_xml=$("${virsh_cmd[@]}" net-dumpxml default --inactive)
if ! printf '%s\n' "$network_xml" | grep -q "192.168.122.1" ||
  ! printf '%s\n' "$network_xml" | grep -q "255.255.255.0"; then
  echo "Le réseau libvirt 'default' n’utilise pas le sous-réseau attendu 192.168.122.0/24." >&2
  echo "Arrêt sans modifier le réseau existant." >&2
  exit 1
fi
