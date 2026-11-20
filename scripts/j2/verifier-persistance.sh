#!/usr/bin/env bash
set -euo pipefail

if [ "${1:-}" != "--confirm-interruption" ]; then
  echo "Ce test redémarre postgres-0 et minio-0 (interruption brève)." >&2
  echo "Après vérification des workloads, relancer avec --confirm-interruption." >&2
  exit 2
fi

read -r -p "Confirmer la recréation de postgres-0 et minio-0 ? [y/N] " confirmation
if [[ ! "$confirmation" =~ ^[Yy]$ ]]; then
  echo "Test annulé."
  exit 0
fi

first=192.168.122.53
key="$HOME/.ssh/mlops-j2"
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
run_id=$(date -u +%Y%m%d%H%M%S)_$$
pg_table="preuve_j2_$run_id"
object_key="preuves/$pg_table.txt"

if [ ! -s "$key" ]; then
  echo "Clé SSH absente : $key." >&2
  exit 1
fi

remote_kubectl() {
  local quoted_args
  printf -v quoted_args ' %q' "$@"
  ssh -o BatchMode=yes -i "$key" "ubuntu@$first" "sudo -n k3s kubectl$quoted_args"
}

remote_kubectl -n mlops get pod/postgres-0 pod/minio-0 >/dev/null
remote_kubectl -n mlops get pvc/data-postgres-0 pvc/data-minio-0

phase=$(remote_kubectl -n mlops get pod/test-s3-j2 --ignore-not-found \
  -o jsonpath='{.status.phase}')
if [ -n "$phase" ] && [ "$phase" != "Running" ]; then
  remote_kubectl -n mlops delete pod test-s3-j2 --wait=true
fi

sql="CREATE TABLE \"$pg_table\" (message text NOT NULL);
     INSERT INTO \"$pg_table\" VALUES ('PostgreSQL J2 : donnees conservees');"
remote_kubectl -n mlops exec postgres-0 -- \
  psql -U mlflow -d mlflow -v ON_ERROR_STOP=1 -c "$sql"

remote_kubectl apply -f - < "$script_dir/test-s3.yaml"
remote_kubectl -n mlops wait --for=condition=Ready pod/test-s3-j2 --timeout=5m
remote_kubectl -n mlops exec -i test-s3-j2 -- env "J2_OBJECT_KEY=$object_key" python - write \
  < "$script_dir/verifier-s3.py"

remote_kubectl -n mlops delete pod postgres-0 --wait=true --timeout=2m
remote_kubectl -n mlops rollout status statefulset/postgres --timeout=5m
pg_result=$(remote_kubectl -n mlops exec postgres-0 -- \
  psql -U mlflow -d mlflow -At -v ON_ERROR_STOP=1 \
  -c "SELECT message FROM \"$pg_table\";")
if [ "$pg_result" != "PostgreSQL J2 : donnees conservees" ]; then
  echo "La vérification PostgreSQL a échoué : $pg_result" >&2
  exit 1
fi
echo "$pg_result"

remote_kubectl -n mlops delete pod minio-0 --wait=true --timeout=2m
remote_kubectl -n mlops rollout status statefulset/minio --timeout=5m
remote_kubectl -n mlops exec -i test-s3-j2 -- env "J2_OBJECT_KEY=$object_key" python - read \
  < "$script_dir/verifier-s3.py"

remote_kubectl -n mlops delete pod test-s3-j2 --wait=true --ignore-not-found
echo "Test PostgreSQL : $pg_table"
echo "Test S3 : s3://mlflow-artifacts/$object_key"
