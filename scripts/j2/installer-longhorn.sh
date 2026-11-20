#!/usr/bin/env bash
set -euo pipefail

first=192.168.122.53
version=v1.13.0
key="$HOME/.ssh/mlops-j2"
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

if [ ! -s "$key" ]; then
  echo "Clé SSH absente : $key." >&2
  exit 1
fi

remote_kubectl() {
  local quoted_args
  printf -v quoted_args ' %q' "$@"
  ssh -o BatchMode=yes -i "$key" "ubuntu@$first" "sudo -n k3s kubectl$quoted_args"
}

remote_kubectl get nodes >/dev/null

existing_manager=$(remote_kubectl -n longhorn-system get daemonset/longhorn-manager --ignore-not-found -o name)
if [ -n "$existing_manager" ]; then
  current_image=$(remote_kubectl -n longhorn-system get daemonset/longhorn-manager \
    -o 'jsonpath={.spec.template.spec.containers[?(@.name=="longhorn-manager")].image}')
  case "$current_image" in
    *":$version") ;;
    *)
      echo "Longhorn déjà installé avec une autre image ($current_image) ; arrêt sans mise à niveau." >&2
      exit 1
      ;;
  esac
fi

ssh -o BatchMode=yes -i "$key" "ubuntu@$first" \
  "curl -fsSL 'https://raw.githubusercontent.com/longhorn/longhorn/$version/deploy/longhorn.yaml' \
    -o '/tmp/longhorn-$version.yaml' &&
   sudo -n k3s kubectl apply -f '/tmp/longhorn-$version.yaml' &&
   sudo -n k3s kubectl -n longhorn-system rollout status daemonset/longhorn-manager --timeout=10m &&
   sudo -n k3s kubectl -n longhorn-system rollout status deployment/longhorn-driver-deployer --timeout=10m &&
   sudo -n k3s kubectl -n longhorn-system wait --for=condition=Ready nodes.longhorn.io --all --timeout=5m"

existing_storageclass=$(remote_kubectl get storageclass longhorn-3copies --ignore-not-found -o name)
if [ -n "$existing_storageclass" ]; then
  current=$(remote_kubectl get storageclass longhorn-3copies \
    -o 'jsonpath={.parameters.numberOfReplicas}/{.parameters.replicaSoftAntiAffinity}/{.parameters.dataEngine}/{.reclaimPolicy}')
  if [ "$current" != "3/disabled/v1/Retain" ]; then
    echo "StorageClass longhorn-3copies existe avec des paramètres différents ($current)." >&2
    echo "Arrêt sans modifier les volumes existants." >&2
    exit 1
  fi
else
  ssh -o BatchMode=yes -i "$key" "ubuntu@$first" \
    'sudo -n k3s kubectl apply --dry-run=server -f -' < "$script_dir/longhorn-3copies.yaml"
  ssh -o BatchMode=yes -i "$key" "ubuntu@$first" \
    'sudo -n k3s kubectl apply -f -' < "$script_dir/longhorn-3copies.yaml"
fi

remote_kubectl get storageclass longhorn-3copies
remote_kubectl -n longhorn-system get nodes.longhorn.io
node_count=$(remote_kubectl -n longhorn-system get nodes.longhorn.io --no-headers | wc -l)
if [ "$node_count" -ne 3 ]; then
  echo "Longhorn voit $node_count nœud(s), 3 sont attendus." >&2
  exit 1
fi
