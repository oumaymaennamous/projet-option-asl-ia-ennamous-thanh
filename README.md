# Projet MLOps : MLflow sur Kubernetes

INSA Centre Val de Loire, 5e année, option ASL-IA, 2026-2027.

Sujet 4 : Plateforme MLOps, MLflow sur Kubernetes.

## Équipe

- **Oumayma Ennamous** : infrastructure (OpenStack, réseau, VM)
- **Thanh Tu Vo** : Kubernetes, stockage, chaîne ML
- **Marwa Boumour** : observabilité

Détail des rôles et suppléances : [docs/plan-travail.md](docs/plan-travail.md).

Statut du plan : proposé, à valider par les trois membres.

## Objectif

Déployer un cluster k3s, PostgreSQL et MinIO avec stockage persistant, puis MLflow pour le suivi des expériences et le registre de modèles (alias `champion`). Le projet inclut l'entraînement automatisé par Job Kubernetes et l'observabilité de la plateforme. L'ensemble doit pouvoir être reconstruit par script depuis ce dépôt.

## Jalons

| Jalon | Échéance |
|---|---|
| J1 — Cadrage | ven. 06/11/2026, 18:00 |
| J2 — Socle en place (k3s, MinIO, PostgreSQL) | ven. 20/11/2026, 18:00 |
| J3 — Cœur du sujet (MVP) | mar. 15/12/2026, 18:00 |
| J4 — Extensions et mesures | ven. 22/01/2027, 18:00 |
| J5 — Reproductibilité | ven. 05/02/2027, 18:00 |

**Gel des fonctionnalités :** 29/01/2027.

**Rendu final :** 12/02/2027, 18:00.

## Structure du dépôt

```text
README.md          présentation du projet et guide du POC
versions.yaml      versions figées
docs/
  adr/             décisions d'architecture (ADR)
  architecture/    propositions d'architecture
  installation/    procédures d'installation
  journal/         journal de séance (AAAA-MM-JJ.md)
  jalons/          checklists et preuves par jalon
  plan-travail.md  rôles et calendrier
  risques.md       registre des risques
scripts/           scripts d'installation (dont openstack-aio.py)
ml/
  src/train.py     code d'entraînement
  requirements.txt dépendances Python
  requirements.lock versions résolues des dépendances
```

## Documents clés

- [Décisions d'architecture (ADR)](docs/adr/)
- [Documents d'architecture](docs/architecture/)
- [Installation d'OpenStack](docs/installation/openstack-aio.md)
- [Rôles et calendrier](docs/plan-travail.md)
- [Registre des risques](docs/risques.md)

## État d'avancement

Phase de cadrage (J1). Aucune installation n'est encore validée sur la machine cible ; les documents d'architecture décrivent une cible.

## Essayer l'entraînement en local (POC)

### Versions MLflow

Les versions du client MLflow, du serveur et du chart Helm doivent rester alignées. La version actuellement retenue est **3.18.0**. Les versions figées sont répertoriées dans [versions.yaml](versions.yaml) ; la décision de stockage et la règle de compatibilité sont détaillées dans [ADR-002](docs/adr/adr-002-mlflow-storage.md).

Avant chaque déploiement, vérifier le chart :

```powershell
helm show chart oci://ghcr.io/mlflow/charts/mlflow --version 3.18.0
```

### Lancer le POC

Prérequis : Python 3.12 (version testée : 3.12.10).

Depuis la racine du dépôt, dans PowerShell :

```powershell
# Créer et activer l'environnement Python
cd ml/
python -m venv .venv
.venv/Scripts/Activate.ps1
pip install -r requirements.txt
```

Dans un premier terminal, lancer le serveur MLflow local (SQLite et stockage local des artefacts pour le POC) :

```powershell
mlflow server --host 127.0.0.1 --port 5000
```

Dans un second terminal, avec le même environnement Python activé, lancer les deux entraînements :

```powershell
python src/train.py --model rf --seed 42
python src/train.py --model ridge --seed 42
```

Sous Linux/macOS, activer l'environnement avec `source ml/.venv/bin/activate`.

L'interface est disponible à [http://127.0.0.1:5000](http://127.0.0.1:5000).
La variable `MLFLOW_TRACKING_URI` permet de viser un autre serveur, par exemple celui qui sera déployé sur k3s à J3.

Résultat attendu : deux runs (`EXP-J3-rf-seed42` et `EXP-J3-ridge-seed42`) dans l'expérience `p3-baseline`, avec les métriques `rmse` et `r2`, le tag `git_commit` et l'artefact `model/`.

## Reconstruction de A à Z

Les procédures seront complétées au fil des jalons :

- **J2 (20/11)** : socle OpenStack, VMs, k3s, PostgreSQL et MinIO ;
- **J3 (15/12)** : MLflow sur le cluster, registre de modèles et alias `champion` ;
- **J5 (05/02)** : reconstruction complète, chronométrée et filmée.

Les secrets ne sont jamais versionnés (par exemple `/etc/kolla/passwords.yml`, kubeconfig et identifiants MinIO). Voir [.gitignore](.gitignore).

## Règles du projet

- Tenir un journal à chaque séance dans `docs/journal/AAAA-MM-JJ.md` avec le créneau, les présences, le point d'équipe et les décisions.
- Créer un tag Git par jalon (`j1`, `j2`, ...) sur `main`, avec une checklist et les preuves correspondantes dans `docs/jalons/jN.md`.
- Faire relire toute modification de script ou de manifeste par un autre membre avant sa fusion dans `main`.
- Tenir un carnet de bord individuel (3 à 5 lignes par semaine).
- Ne jamais ajouter de secret à Git.
- Garder l'ensemble reconstructible par script depuis le dépôt.
