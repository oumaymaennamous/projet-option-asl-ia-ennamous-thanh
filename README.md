# Projet Option ASL-IA
## Plateforme MLOps : MLflow sur Kubernetes (Sujet 4)

INSA Centre Val de Loire, 5e année, option ASL-IA, 2026-2027.

**Équipe :** Oumayma Ennamous, Thanh Tu Vo, Marwa Boumour.
**Cadrage actualisé :** 4 novembre 2026.
**J1 :** vendredi 6 novembre 2026 à 18 h, selon le mail de réorganisation.

La plateforme suit les entraînements, compare les résultats et gère les versions de modèles. Le cas d'usage principal est la prédiction du départ des clients télécoms (Telco Customer Churn), avec régression logistique et Random Forest. Un POC local sur California Housing sert à valider la chaîne de suivi MLflow.

**Architecture de référence actuelle : KVM/libvirt → trois VM Ubuntu → un cluster K3s → MLflow, PostgreSQL, MinIO et Longhorn.** Streamlit et KServe sont des extensions après le MVP. Prometheus et Grafana portent le volet observabilité du groupe.

## Équipe et rôles

- **Oumayma Ennamous** : infrastructure (KVM/libvirt, réseau, VM, K3s)
- **Thanh Tu Vo** : Kubernetes, stockage, chaîne ML
- **Marwa Boumour** : observabilité

Détail des rôles et suppléances : [docs/plan-travail.md](docs/plan-travail.md) (statut : proposé, à valider par les trois membres).

## Jalons

| Jalon | Échéance |
|---|---|
| J1 Cadrage | ven. 06/11/2026, 18:00 |
| J2 Socle en place (k3s, MinIO, PostgreSQL) | ven. 20/11/2026, 18:00 (oral le matin) |
| J3 Cœur du sujet (MVP) | mar. 15/12/2026, 18:00 |
| J4 Extensions et mesures | ven. 22/01/2027, 18:00 |
| J5 Reproductibilité | ven. 05/02/2027, 18:00 |

Gel des fonctionnalités : 29/01/2027. Rendu final : 12/02/2027, 18:00.

## Dossier J1

| Attendu | Document |
|---|---|
| Architecture courte et schéma | [Proposition Oumayma V3 (KVM/libvirt)](docs/architecture/proposition-oumayma-v3.md) |
| Choix du socle | [ADR-000 : KVM/libvirt ou OpenStack](docs/adr/ADR-000-socle-kvm-libvirt.md) |
| Distribution Kubernetes | [ADR-001 : K3s ou kubeadm](docs/adr/ADR-001-k3s-vs-kubeadm.md) |
| Stockage MLflow | [ADR-002 : PostgreSQL, MinIO et Longhorn](docs/adr/ADR-002-stockage-mlflow.md) |
| Observabilité | [ADR-003 : Prometheus et Grafana](docs/adr/ADR-003-observabilite.md) |
| Risques | [Registre des risques](docs/risques.md) |
| Travail et rôles | [Plan de travail](docs/plan-travail.md) |
| Validation du jalon et preuves | [Checklist J1](docs/jalons/J1-checklist.md) |
| Journal de préparation | [4 novembre 2026](docs/journal/2026-11-04.md) |

## Réalisé, proposé et restant à faire

**Réalisé (avec preuves à verser dans `docs/jalons/preuves/`) :**
- POC local MLflow (Thanh Tu) : serveur MLflow local (client + serveur 3.18.0, SQLite), 4 runs vérifiés :
  - **Housing** (régression, historique) : `rf` et `ridge`, métriques `rmse` / `r2`
  - **Churn** (classification, cible J3) : `logreg` et `rf`, métriques `accuracy` / `precision` / `recall` / `f1` / `roc_auc` / `f1_thr_30-50-70`
  Captures dans `docs/jalons/preuves/` (7 PNG). Détail et versions : [ml/README.md](ml/README.md).
- Laboratoire VMware (Oumayma) : trois serveurs K3s, Headlamp, Longhorn, PostgreSQL, MinIO et MLflow testés, persistance PostgreSQL et MinIO vérifiée après recréation des pods. Les captures, manifests exacts et sorties ne sont pas encore versés dans ce dépôt.

**Proposé, non validé :**
- Socle KVM/libvirt sur les machines du groupe. L'inventaire matériel, le dimensionnement et le déploiement restent à réaliser.
- Telco Customer Churn comme cas d'usage principal pour J3 (source et licence du jeu de données à documenter).

**Restant à faire :** registre et promotion du modèle (alias `champion`), automatisation J4, observabilité, extensions.

## Versions MLflow

Les versions du client MLflow, du serveur et du chart Helm doivent rester alignées. Version cible : **3.18.0** (chart `oci://ghcr.io/mlflow/charts/mlflow` vérifié le 04/11/2026 avec `helm show chart`). Le client Python **3.18.0** a été validé de bout en bout le 2026-11-05 avec `ml/src/train.py` (4 runs, expériences `p3-baseline` et `p3-churn`). Les versions réellement testées sont figées dans [versions.yaml](versions.yaml). Décision et règle de compatibilité : [ADR-002](docs/adr/ADR-002-stockage-mlflow.md).

## Reproductibilité attendue pour J2 à J5

Chaîne cible : inventaire et prérequis → VM cloud-init/libvirt → configuration Ansible/K3s → stockage (Longhorn) → PostgreSQL et MinIO → MLflow → entraînement et tests. Les versions et images doivent être figées, les Secrets fournis hors Git, puis une reconstruction complète testée.

**Ce README n'est pas encore un guide d'installation de A à Z.** Les scripts KVM/Ansible, manifests et la commande `make demo` ne sont pas encore livrés ; leur avancement est suivi dans le [plan de travail](docs/plan-travail.md).

Les secrets ne sont jamais versionnés (identifiants PostgreSQL et MinIO, kubeconfig, mots de passe). Voir [.gitignore](.gitignore).

## Structure du dépôt

```text
README.md            présentation du projet
versions.yaml        versions figées
docs/
  adr/               décisions d'architecture (ADR)
  architecture/      propositions d'architecture (V1, V2, V3)
  archive/openstack/ procédure OpenStack historique (obsolète)
  journal/           journal de séance (AAAA-MM-JJ.md)
  jalons/            checklists et preuves par jalon
  plan-travail.md    rôles et calendrier
  risques.md         registre des risques
ml/                  POC et code d'entraînement (voir ml/README.md)
```

## Historique et chemins conservés

- [V1](docs/architecture/proposition-oumayma.md) et [V2 OpenStack](docs/architecture/proposition-oumayma-v2.md) : propositions historiques, remplacées pour le cadrage courant par la V3.
- [OpenStack historique](docs/archive/openstack/README.md) : `openstack-aio.py` et sa procédure, conservés pour comparaison, jamais exécutés sur une machine réelle ; ne constituent pas la procédure KVM retenue.
- [Journal du 23 octobre](docs/journal/2026-10-23.md) : décisions de séance historiques, non réécrites.

## Règles du projet

- Journal de séance à chaque créneau officiel dans `docs/journal/AAAA-MM-JJ.md`.
- Un tag Git par jalon (`j1`, `j2`, ...) sur `main`, avec checklist et preuves dans `docs/jalons/`.
- Toute modification de script ou de manifeste est relue par un autre membre avant fusion dans `main`.
- Carnet de bord individuel (3 à 5 lignes par semaine).
- Aucun secret dans Git ; tout reconstructible par script depuis le dépôt.

L'acceptation du J1 et le tag `j1` restent soumis à la revue de l'équipe et aux preuves listées. Un document rédigé ne constitue pas une validation du professeur.