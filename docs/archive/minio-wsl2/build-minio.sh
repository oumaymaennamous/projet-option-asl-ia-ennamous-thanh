#!/usr/bin/env bash
# Compile la source MinIO épinglée, construit l'image locale et l'archive pour transfert.
set -euo pipefail

MINIO_TAG="${MINIO_TAG:-RELEASE.2025-10-15T17-29-55Z}"
MINIO_COMMIT="${MINIO_COMMIT:-9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a}"
MINIO_REPO="${MINIO_REPO:-https://github.com/minio/minio.git}"
GO_MIN_VERSION="${GO_MIN_VERSION:-1.24.8}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DOCKERFILE="$SCRIPT_DIR/minio-Dockerfile.custom"
WORKDIR="${WORKDIR:-$HOME/projects}"
SRC_DIR="$WORKDIR/minio-$MINIO_TAG"
TAR_FILE="$WORKDIR/minio-image.tar"
IMAGE="minio:$MINIO_TAG"

for tool in docker go make git curl file; do
    command -v "$tool" >/dev/null || {
        echo "Outil manquant : $tool" >&2
        exit 1
    }
done
docker info >/dev/null 2>&1 || {
    echo "Docker daemon injoignable. Vérifier Docker Desktop et l'intégration WSL2." >&2
    exit 1
}
[ -f "$DOCKERFILE" ] || {
    echo "Dockerfile manquant : $DOCKERFILE" >&2
    exit 1
}

go_version="$(go version | awk '{sub(/^go/, "", $3); print $3}')"
if ! printf '%s\n%s\n' "$GO_MIN_VERSION" "$go_version" | sort -V -C; then
    echo "AVERTISSEMENT : go $go_version est inférieur à $GO_MIN_VERSION." >&2
fi
echo "[env] go=$go_version docker=$(docker version --format '{{.Server.Version}}')"

mkdir -p "$WORKDIR"
if [ ! -d "$SRC_DIR/.git" ]; then
    echo "[src] clone $MINIO_TAG"
    git clone --depth 1 --branch "$MINIO_TAG" "$MINIO_REPO" "$SRC_DIR"
fi
actual_commit="$(git -C "$SRC_DIR" rev-parse HEAD)"
if [ "$actual_commit" != "$MINIO_COMMIT" ]; then
    echo "Commit inattendu pour $MINIO_TAG : $actual_commit (attendu $MINIO_COMMIT)." >&2
    exit 1
fi

echo "[build] MinIO $MINIO_TAG ($actual_commit)"
(cd "$SRC_DIR" && GOOS=linux GOARCH=amd64 make build)
if ! file "$SRC_DIR/minio" | grep -q 'ELF 64-bit.*x86-64'; then
    echo "Le binaire compilé n'est pas un ELF x86-64 Linux :" >&2
    file "$SRC_DIR/minio" >&2
    exit 1
fi

cp -- "$DOCKERFILE" "$SRC_DIR/Dockerfile.custom"
docker build -f "$SRC_DIR/Dockerfile.custom" -t "$IMAGE" "$SRC_DIR"
env_vars="$(docker inspect --format '{{.Config.Env}}' "$IMAGE")"
if echo "$env_vars" | grep -qi 'MINIO_ROOT'; then
    echo "L'image contient des variables MINIO_ROOT_*." >&2
    exit 1
fi
digest="$(docker inspect --format '{{.Id}}' "$IMAGE")"
echo "[image] $IMAGE ($digest)"

echo "[test] healthcheck"
docker run --rm -d --name minio-build-healthcheck \
    -p 19000:9000 \
    -e MINIO_ROOT_USER=tmp -e MINIO_ROOT_PASSWORD=tmp-tmp-tmp \
    "$IMAGE" server /data >/dev/null
code=""
for _ in {1..10}; do
    sleep 1
    code="$(curl -s -o /dev/null -w '%{http_code}' \
        http://localhost:19000/minio/health/live || true)"
    [ "$code" = 200 ] && break
done
docker stop minio-build-healthcheck >/dev/null 2>&1 || true
if [ "$code" != 200 ]; then
    echo "Healthcheck échoué (HTTP $code)." >&2
    exit 1
fi

docker save "$IMAGE" -o "$TAR_FILE"
echo "[save] $TAR_FILE"
printf 'Build terminé : %s\nCommit : %s\nDigest : %s\nArchive : %s\n' \
    "$IMAGE" "$actual_commit" "$digest" "$TAR_FILE"
