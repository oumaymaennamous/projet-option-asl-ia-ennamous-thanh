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

**Prochain jalon, J2** · Déployer K3s, PostgreSQL et MinIO sur la cible KVM/libvirt et vérifier la persistance des données.

[Historique des propositions d’architecture](https://github.com/oumaymaennamous/projet-option-asl-ia-ennamous-thanh/tree/373598bca0d0694c221b03503b91ae1011d9541f/docs/architecture)
