#!/usr/bin/env bash
set -euo pipefail

first=192.168.122.53
key="$HOME/.ssh/mlops-j2"
image=localhost/minio-j2:2025-10-15
nodes=(
  "k3s-server-1 192.168.122.53"
  "k3s-server-2 192.168.122.70"
  "k3s-server-3 192.168.122.152"
)
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

remote_kubectl get storageclass longhorn-3copies >/dev/null
for entry in "${nodes[@]}"; do
  read -r vm ip <<<"$entry"
  if ! ssh -o BatchMode=yes -i "$key" "ubuntu@$ip" \
    "sudo -n k3s ctr images ls -q | grep -Fx '$image' >/dev/null"; then
    echo "Image MinIO absente sur $vm ($ip). Lancer import-minio.sh." >&2
    exit 1
  fi
done

namespace=$(remote_kubectl get namespace mlops --ignore-not-found -o name)
if [ -z "$namespace" ]; then
  remote_kubectl create namespace mlops
fi

postgres_secret=$(remote_kubectl -n mlops get secret postgres-auth --ignore-not-found -o name)
if [ -z "$postgres_secret" ]; then
  postgres_statefulset=$(remote_kubectl -n mlops get statefulset/postgres --ignore-not-found -o name)
  postgres_pvc=$(remote_kubectl -n mlops get pvc/data-postgres-0 --ignore-not-found -o name)
  if [ -n "$postgres_statefulset" ] || [ -n "$postgres_pvc" ]; then
    echo "Secret postgres-auth absent alors que des données PostgreSQL existent ; arrêt sans créer un nouveau mot de passe." >&2
    exit 1
  fi
  echo "Création du secret PostgreSQL (mot de passe aléatoire, non affiché)."
  openssl rand -hex 24 | tr -d '\n' |
    ssh -o BatchMode=yes -i "$key" "ubuntu@$first" \
      'sudo -n k3s kubectl -n mlops create secret generic postgres-auth --from-file=password=/dev/stdin'
fi
if ! ssh -o BatchMode=yes -i "$key" "ubuntu@$first" \
  "sudo -n k3s kubectl -n mlops get secret postgres-auth -o jsonpath='{.data.password}' | grep -q ."; then
  echo "Le Secret postgres-auth est absent ou ne contient pas la clé password." >&2
  exit 1
fi

minio_secret=$(remote_kubectl -n mlops get secret minio-secret --ignore-not-found -o name)
if [ -z "$minio_secret" ]; then
  minio_statefulset=$(remote_kubectl -n mlops get statefulset/minio --ignore-not-found -o name)
  minio_pvc=$(remote_kubectl -n mlops get pvc/data-minio-0 --ignore-not-found -o name)
  if [ -n "$minio_statefulset" ] || [ -n "$minio_pvc" ]; then
    echo "Secret minio-secret absent alors que MinIO existe ; arrêt sans remplacer ses identifiants." >&2
    exit 1
  fi
  read -r -p "Identifiant MinIO [mlops-s3] : " minio_user
  minio_user=${minio_user:-mlops-s3}
  read -r -s -p "Mot de passe MinIO (au moins 8 caractères) : " minio_password
  printf '\n'
  if [ "${#minio_password}" -lt 8 ]; then
    unset minio_password
    echo "Le mot de passe doit contenir au moins 8 caractères." >&2
    exit 1
  fi
  printf 'MINIO_ROOT_USER=%s\nMINIO_ROOT_PASSWORD=%s\n' "$minio_user" "$minio_password" |
    ssh -o BatchMode=yes -i "$key" "ubuntu@$first" \
      'sudo -n k3s kubectl -n mlops create secret generic minio-secret --from-env-file=/dev/stdin'
  unset minio_password
fi
for secret_key in MINIO_ROOT_USER MINIO_ROOT_PASSWORD; do
  if ! ssh -o BatchMode=yes -i "$key" "ubuntu@$first" \
    "sudo -n k3s kubectl -n mlops get secret minio-secret -o jsonpath='{.data.$secret_key}' | grep -q ."; then
    echo "Le Secret minio-secret est absent ou ne contient pas la clé $secret_key." >&2
    exit 1
  fi
done

ssh -o BatchMode=yes -i "$key" "ubuntu@$first" \
  'sudo -n k3s kubectl apply --dry-run=server -f -' < "$script_dir/postgres.yaml"
ssh -o BatchMode=yes -i "$key" "ubuntu@$first" \
  'sudo -n k3s kubectl apply --dry-run=server -f -' < "$script_dir/minio.yaml"

ssh -o BatchMode=yes -i "$key" "ubuntu@$first" \
  'sudo -n k3s kubectl apply -f -' < "$script_dir/postgres.yaml"
remote_kubectl -n mlops rollout status statefulset/postgres --timeout=10m
remote_kubectl -n mlops wait --for=jsonpath='{.status.phase}'=Bound pvc/data-postgres-0 --timeout=5m

ssh -o BatchMode=yes -i "$key" "ubuntu@$first" \
  'sudo -n k3s kubectl apply -f -' < "$script_dir/minio.yaml"
remote_kubectl -n mlops rollout status statefulset/minio --timeout=10m
remote_kubectl -n mlops wait --for=jsonpath='{.status.phase}'=Bound pvc/data-minio-0 --timeout=5m
remote_kubectl -n mlops get pods,pvc,svc
