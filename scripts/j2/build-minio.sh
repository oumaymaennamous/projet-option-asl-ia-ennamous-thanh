#!/usr/bin/env bash
set -euo pipefail

image=localhost/minio-j2:2025-10-15
archive="$HOME/mlops-j2/minio-j2.tar"
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

command -v podman >/dev/null || {
  echo "podman est requis pour construire l’image MinIO." >&2
  exit 1
}

sudo -v
mkdir -p "$(dirname "$archive")"
sudo podman build --file "$script_dir/minio.Containerfile" --tag "$image" "$script_dir"
sudo podman run --rm "$image" --version
sudo podman save --format docker-archive --output "$archive" "$image"
sudo chown "$(id -u):$(id -g)" "$archive"
chmod 600 "$archive"
sha256sum "$archive"
echo "Archive prête : $archive"
