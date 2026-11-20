#!/usr/bin/env bash
set -euo pipefail

TAR="${1:-/tmp/minio-image.tar}"
KEY="${SSH_KEY:-$HOME/.ssh/mlops-j2}"
TAG_FILTER="minio:RELEASE.2025-10-15T17-29-55Z"
NODES=(
  "ubuntu@192.168.122.53"
  "ubuntu@192.168.122.70"
  "ubuntu@192.168.122.152"
)

[ -f "$TAR" ] || { echo "Tar introuvable : $TAR" >&2; exit 1; }
echo "[local] $TAR ($(du -h "$TAR" | cut -f1))"

for node in "${NODES[@]}"; do
    echo "==== $node ===="

    echo "[$node] copie"
    scp -q -i "$KEY" "$TAR" "$node:/tmp/minio-image.tar"

    echo "[$node] import containerd"
    ssh -i "$KEY" "$node" "sudo k3s ctr images import /tmp/minio-image.tar" \
        >/dev/null

    echo "[$node] vérification"
    if ! ssh -i "$KEY" "$node" "sudo k3s ctr images ls -q | grep -q '^docker.io/library/$TAG_FILTER'"; then
        echo "Échec : image absente sur $node" >&2
        exit 1
    fi
    ssh -i "$KEY" "$node" \
        "sudo k3s ctr images ls | grep '$TAG_FILTER'" || true
done

echo
echo "Import OK sur les 3 nœuds."
echo "Prochaine étape (sur n2, via SSH vers k3s-server-1) :"
echo "  1) kubectl -n mlops create secret generic minio-credentials \\"
echo "       --from-literal=MINIO_ROOT_USER=admin \\"
echo "       --from-literal=MINIO_ROOT_PASSWORD='<mot-de-passe-fort>'"
echo "  2) kubectl apply -f scripts/j2/minio.yaml"
echo "  3) kubectl -n mlops rollout status statefulset/minio"