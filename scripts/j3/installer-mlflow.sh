#!/usr/bin/env bash
set -euo pipefail

# À lancer sur n2. Déploie MLflow (chart officiel) sur le cluster K3s.
first=192.168.122.53
vms=(192.168.122.53 192.168.122.70 192.168.122.152)
key="$HOME/.ssh/mlops-j2"
chart=oci://ghcr.io/mlflow/charts/mlflow
chart_version=3.18.0
helm_version=v3.22.1
helm_sha256=896cf63684a42a723d61c980369d6e588330927deb13676ca0d85006dd6da0ea
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

[ -s "$key" ] || { echo "Clé SSH absente : $key." >&2; exit 1; }
[ -s "$script_dir/values-j3.yaml" ] || { echo "values-j3.yaml absent." >&2; exit 1; }

ssh_vm() { local ip=$1; shift; ssh -o BatchMode=yes -i "$key" "ubuntu@$ip" "$@"; }
remote_kubectl() {
  local quoted_args
  printf -v quoted_args ' %q' "$@"
  ssh_vm "$first" "sudo -n k3s kubectl$quoted_args"
}

# 1. DNS : contournement temporaire, perdu au redémarrage d'une VM (cf. minio-j2.md, 1 bis)
dns_fixed=false
for ip in "${vms[@]}"; do
  if ! ssh_vm "$ip" 'getent ahostsv4 ghcr.io >/dev/null'; then
    echo "DNS : ghcr.io non résolu sur $ip, application du contournement."
    ssh_vm "$ip" 'sudo -n resolvectl dns ens3 1.1.1.1 && sudo -n resolvectl flush-caches && getent ahostsv4 ghcr.io | head -1'
    dns_fixed=true
  fi
done
if [ "$dns_fixed" = true ]; then
  remote_kubectl -n kube-system rollout restart deployment/coredns
  remote_kubectl -n kube-system rollout status deployment/coredns --timeout=2m
fi

# 2. Helm (version et empreinte SHA-256 figées, sans script flottant)
if ! ssh_vm "$first" "command -v helm >/dev/null && helm version --short | grep -q '^${helm_version}+'"; then
  ssh_vm "$first" "
    set -euo pipefail
    tmp_dir=\$(mktemp -d)
    trap 'rm -rf \"\$tmp_dir\"' EXIT
    curl -fsSL 'https://get.helm.sh/helm-${helm_version}-linux-amd64.tar.gz' -o \"\$tmp_dir/helm.tgz\"
    echo '${helm_sha256}  '\"\$tmp_dir/helm.tgz\" | sha256sum -c -
    tar -xzf \"\$tmp_dir/helm.tgz\" -C \"\$tmp_dir\"
    sudo -n install -m 0755 \"\$tmp_dir/linux-amd64/helm\" /usr/local/bin/helm
  "
fi

# 3. Prérequis du namespace
remote_kubectl -n mlops get secret postgres-auth minio-secret >/dev/null
remote_kubectl -n mlops get statefulset/postgres statefulset/minio >/dev/null

# 4. Secret mlflow-db (URI PostgreSQL), créé seulement s'il manque
if [ -z "$(remote_kubectl -n mlops get secret mlflow-db --ignore-not-found -o name)" ]; then
  echo "Création du Secret mlflow-db (mot de passe non affiché)."
  remote_kubectl -n mlops get secret postgres-auth -o jsonpath='{.data.password}' | base64 -d |
    { printf 'uri=postgresql://mlflow:'; cat; printf '@postgres.mlops.svc.cluster.local:5432/mlflow'; } |
    ssh_vm "$first" 'sudo -n k3s kubectl -n mlops create secret generic mlflow-db --from-env-file=/dev/stdin'
fi

# 5. Déploiement : simulation côté serveur puis installation
helm_cmd="sudo -n env KUBECONFIG=/etc/rancher/k3s/k3s.yaml helm upgrade --install mlflow $chart --version $chart_version -n mlops -f - --timeout 10m"
ssh_vm "$first" "$helm_cmd --dry-run=server >/dev/null" < "$script_dir/values-j3.yaml"
ssh_vm "$first" "$helm_cmd --wait" < "$script_dir/values-j3.yaml"

remote_kubectl -n mlops get pods,svc -o wide
ssh_vm "$first" 'sudo -n env KUBECONFIG=/etc/rancher/k3s/k3s.yaml helm list -n mlops'