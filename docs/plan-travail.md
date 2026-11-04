# Plan de travail et répartition des rôles

- Date : 2026-11-04
- Équipe : Oumayma Ennamous, Thanh Tu Vo, Marwa Boumour
- Sujet 4 : Plateforme MLOps, MLflow sur Kubernetes
- Statut : proposé (à valider par les trois membres)

## 1. Rôles

| Membre | Pilote de | Suppléant de |
|---|---|---|
| Oumayma Ennamous | Infrastructure : OpenStack (Kolla-Ansible), réseau, VM, automatisation, ADR-000 | Thanh Tu |
| Thanh Tu Vo | Kubernetes et chaîne ML : k3s, stockage persistant, PostgreSQL, MinIO, MLflow, `train.py`, registre, Jobs, ADR-001, ADR-002 | Marwa |
| Marwa Boumour | Observabilité : Prometheus, Grafana, journaux, alertes, pannes contrôlées, mesures J4, ADR-003 | Oumayma |

Tâches transverses partagées : dépôt Git, README « de A à Z », journal, registre des risques, rapport.

Le suppléant relit le travail du pilote et doit pouvoir le remplacer : tout membre peut être interrogé sur toute l'architecture (oral du 20/11).
Les rôles peuvent être rééquilibrés après un jalon ; tout changement est noté dans le journal.

## 2. Règles de travail

- Point d'équipe de 15 min au début de chaque créneau ; 5 lignes dans `docs/journal/AAAA-MM-JJ.md` (fait, bloqué, prévu).
- Relecture croisée : toute modification de script ou de manifest est relue par un autre membre avant fusion dans `main`.
- Règle des 3 heures : bloqué plus de 3 h effectives, on demande de l'aide à l'équipe ; bloqué plus d'un créneau sur une étape critique, on applique le plan B de l'ADR concerné et on le note dans le journal.
- Un jalon est validé par un tag Git (`jN`) posé sur `main` et par `docs/jalons/jN.md` (checklist avec preuves) ; point sans preuve = non validé.
- Carnet de bord individuel : 3 à 5 lignes par semaine (heures, tâches, difficultés).
- Aucun secret dans Git (mots de passe, `passwords.yml`, kubeconfig, clés).
- Tout doit être reconstructible par script depuis le dépôt.

## 3. Calendrier

| Jalon | Échéance | Contenu attendu |
|---|---|---|
| J1 Cadrage | ven. 06/11, 18:00 | Dépôt structuré, architecture courte, 2 ADR minimum, risques, plan et rôles |
| J2 Socle | ven. 20/11, 18:00 | Socle + k3s + MinIO + PostgreSQL persistants, reconstruits par script ; oral J1/J2 le matin |
| J3 MVP | mar. 15/12, 18:00 | MLflow sur le cluster, runs comparés, modèle enregistré et promu ; Go/No-Go |
| Rédaction | ven. 18/12 | Sections du rapport J1–J3 ; sauvegarde avant les vacances |
| J4 Extensions et mesures | ven. 22/01, 18:00 | Entraînement automatisé, hyperparamètres, mesures (≥ 3 répétitions, médiane et dispersion) |
| Gel | ven. 29/01 | Plus aucune nouvelle fonctionnalité |
| J5 Reproductibilité | ven. 05/02, 18:00 | Destruction puis reconstruction chronométrée et filmée, par un membre qui ne l'a jamais faite |
| Rendu final | ven. 12/02, 18:00 | Rapport, dépôt, `make demo` ; soutenance entre le 8 et le 19/02 |

## 4. Plan détaillé jusqu'à J2

| Période | Oumayma (infra) | Thanh Tu (K8s, ML) | Marwa (observabilité) |
|---|---|---|---|
| 04–05/11 | ADR-000, architecture courte, vérification de la machine | ADR-001, plan de travail, README, `versions.yaml` | ADR-003, rédaction des risques d'observabilité |
| 05/11 soir | relecture croisée, fusion dans `main` | idem | idem |
| 06/11 | `docs/jalons/j1.md` ensemble, journal, carnets, tag `j1` avant 18:00 | idem | idem |
| 07–13/11 | `openstack-aio.py check` sur la machine réelle, déploiement OpenStack, VM | scripts d'installation k3s préparés et testés en local (VM ou k3d), manifests PostgreSQL et MinIO | prototype Prometheus/Grafana en local, liste des métriques et alertes |
| 14–19/11 | VM créées par script, réseau, accès SSH | k3s sur les VM, PVC testés (redémarrage de pod), PostgreSQL et MinIO | premières métriques du cluster |
| 20/11 | oral le matin ; tag `j2` avant 18:00 | idem | idem |

Date limite de bascule vers le plan B du socle (KVM/libvirt) : [à fixer dans l'ADR-000, ex. 11/11 si `openstack server list` ne fonctionne pas].

## 5. Après J2 (vue d'ensemble)

| Jalon | Oumayma | Thanh Tu | Marwa |
|---|---|---|---|
| J3 (15/12) | support infra, sauvegardes | MLflow sur le cluster, ≥ 2 familles d'algorithmes, runs comparés, alias `champion` | dashboards, premières alertes |
| J4 (22/01) | automatisation, CI | Job Kubernetes, recherche d'hyperparamètres, analyse | protocole de mesure, pannes contrôlées, coût de l'observabilité |
| J5 (05/02) | scripts de reconstruction | idem | idem ; la reconstruction est faite par un membre qui n'a jamais installé la partie concernée |
| Rendu (12/02) | rapport, `make demo` | rapport, soutenance | rapport, soutenance |

## 6. Rituels et suivi

- Revue du plan à la fin de chaque jalon (rééquilibrage des rôles si besoin).
- Créneaux officiels : [à confirmer dans l'emploi du temps] ; hors créneaux, travail sur temps libre.
- Canal de communication : [ex. groupe de discussion] ; décisions importantes reportées dans le journal ou dans un ADR.