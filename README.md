# projet-option-asl-ia-ennamous-thanh

## Plateforme MLOps : MLflow sur Kubernetes — Sujet 4

**Équipe :** Oumayma Ennamous, Thanh Tu Vo, Marwa Boumour.
**Cadrage actualisé :** 4 novembre 2026, branche `oumayma`.
**J1 :** vendredi 6 novembre 2026 à 18 h, selon le mail de réorganisation.

La plateforme suit les entraînements, compare les résultats et gère les versions de modèles. Le cas d’usage est la prédiction du départ des clients télécoms, avec régression logistique et Random Forest.

**Architecture de référence actuelle : KVM/libvirt → trois VM Ubuntu → un cluster K3s → MLflow, PostgreSQL, MinIO et Longhorn.** Streamlit et KServe sont des extensions après le MVP. Prometheus et Grafana portent le volet observabilité du groupe.

## Dossier J1

| Attendu | Document |
|---|---|
| Architecture courte et schéma | [Proposition Oumayma V3 — KVM/libvirt](docs/architecture/proposition-oumayma-v3.md) |
| Choix du socle | [ADR-000 — KVM/libvirt ou OpenStack](docs/adr/ADR-000-socle-kvm-libvirt.md) |
| Distribution Kubernetes | [ADR-001 — K3s ou kubeadm](docs/adr/ADR-001-k3s-vs-kubeadm.md) |
| Stockage MLflow | [ADR-002 — PostgreSQL, MinIO et Longhorn](docs/adr/ADR-002-stockage-mlflow.md) |
| Observabilité | [ADR-003 — Prometheus et Grafana](docs/adr/ADR-003-observabilite.md) |
| Risques | [Registre des risques](docs/risques.md) |
| Travail et rôles | [Plan de travail](docs/plan-travail.md) |
| Validation du jalon et preuves | [Checklist J1](docs/jalons/J1-checklist.md) |
| Journal de préparation | [4 novembre 2026](docs/journal/2026-11-04.md) |

## Réalisé, proposé et restant à faire

Un laboratoire VMware a permis à Oumayma de tester trois serveurs K3s, Headlamp, Longhorn, PostgreSQL, MinIO et MLflow. La persistance PostgreSQL et MinIO a été testée après recréation des pods. Le suivi des entraînements est déclaré fonctionnel dans les échanges ; les captures, manifests exacts et sorties ne sont pas encore versés dans ce dépôt.

Le socle KVM/libvirt est la cible proposée pour les machines du groupe. L’inventaire matériel, le dimensionnement et le déploiement sur cette cible restent à réaliser. Le registre et la promotion du modèle, l’automatisation J4, l’observabilité et les extensions ne sont pas présentés comme validés par cette documentation.

## Reproductibilité attendue pour J2–J5

La chaîne cible est : inventaire et prérequis → VM cloud-init/libvirt → configuration Ansible/K3s → stockage → PostgreSQL/MinIO → MLflow → entraînement et tests. Les versions et images doivent être figées, les Secrets fournis hors Git, puis une reconstruction complète testée.

**Ce README n’est pas encore un guide d’installation de A à Z.** Les scripts KVM/Ansible, manifests et commandes `make demo` ne sont pas ajoutés par ce commit documentaire. Leur livraison et leurs preuves sont suivies dans le plan.

## Historique et chemins conservés

- [V1](docs/architecture/proposition-oumayma.md) et [V2 OpenStack](docs/architecture/proposition-oumayma-v2.md) : propositions historiques, remplacées pour le cadrage courant par la V3.
- [Installation OpenStack historique](docs/installation/openstack-aio.md) et `scripts/openstack-aio.py` : conservés pour comparaison ; ne constituent pas la procédure KVM retenue.
- [Journal du 23 octobre](docs/journal/2026-10-23.md) : décisions de séance historiques, non réécrites.

L’acceptation du J1 et le tag `j1` restent soumis à la revue de l’équipe et aux preuves listées. Un document rédigé ne constitue pas une validation du professeur.
