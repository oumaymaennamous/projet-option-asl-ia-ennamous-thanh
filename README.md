# Plateforme MLOps avec MLflow sur Kubernetes

**Sujet 4 · Option ASL-IA · INSA Centre-Val de Loire**

La plateforme suit les entraînements, compare les résultats et gère les versions de modèles. **Telco Customer Churn** est le cas principal. **California Housing** sert de preuve de concept pour le suivi d’expériences.

## Architecture

- **KVM/libvirt et K3s** hébergent la plateforme sur trois VM Ubuntu.
- **MLflow** suit les expériences et versionne les modèles. **PostgreSQL** conserve les métadonnées, **MinIO** stocke les artefacts et **Longhorn** réplique leurs volumes persistants.
- **Prometheus, Grafana et Alertmanager** supervisent le cluster. Loki reste optionnel selon les ressources. KServe et Streamlit sont des extensions prévues après J3.

## Dossier J1

| Livrable | Document |
|---|---|
| Architecture et schéma | [Architecture générale](docs/architecture/architecture-v0.md) |
| Décisions et plans B | [Socle](docs/adr/ADR-000-socle-kvm-libvirt.md) · [Kubernetes](docs/adr/ADR-001-k3s-vs-kubeadm.md) · [Stockage](docs/adr/ADR-002-stockage-mlflow.md) · [Observabilité](docs/adr/ADR-003-observabilite.md) |
| Organisation | [Risques](docs/risques.md) · [Planning et rôles](docs/plan-travail.md) |
| Suivi | [Checklist et preuves J1](docs/jalons/J1-checklist.md) · [POC MLflow](ml/README.md) · [Versions](versions.yaml) |

**Équipe** · Oumayma Ennamous (infrastructure), Thanh Tu Vo (Kubernetes et chaîne ML), Marwa Boumour (observabilité).

**J2** · K3s, Longhorn, PostgreSQL et MinIO sont déployés sur la cible KVM/libvirt (n2). Persistance prouvée sur le cluster pour PostgreSQL (10/11) et MinIO (18/11). MLflow est validé en local (mode proxy, PostgreSQL, MinIO) ; son déploiement sur le cluster est prévu pour J3. [Journal du 10 novembre](docs/journal/2026-11-10.md) · [Preuves persistance](docs/jalons/preuves/persistance.md) · [Procédure MinIO](scripts/j2/minio-j2.md)

**J3** · MLflow 3.18.0 est déployé sur K3s (Helm, mode proxy, PostgreSQL et MinIO). Six runs Telco Churn comparés, modèle `telco-churn` v1 avec alias `champion` (v2 depuis le 27/11). Preuves versées ; tag `j3` posé après revue croisée. [Preuves MLflow](docs/jalons/preuves/mlflow.md) · [Checklist J3](docs/jalons/J3-checklist.md)

[Historique des propositions d’architecture](https://github.com/oumaymaennamous/projet-option-asl-ia-ennamous-thanh/tree/373598bca0d0694c221b03503b91ae1011d9541f/docs/architecture)
