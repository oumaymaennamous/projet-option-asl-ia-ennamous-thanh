# Plan de travail et répartition des rôles

- Date : 2026-11-04
- Équipe : Oumayma Ennamous, Thanh Tu Vo, Marwa Boumour
- Sujet 4 : Plateforme MLOps, MLflow sur Kubernetes
- Statut : proposé (à valider par les trois membres)

Architecture de référence : KVM/libvirt, trois VM Ubuntu, K3s, Longhorn, PostgreSQL, MinIO, MLflow (voir ADR-000 et la proposition V3). Cette répartition est une proposition, sans présumer d'une validation ni de travaux déjà réalisés par les autres membres.

## 1. Rôles, suppléances et relectures

| Membre | Pilote de | Livrables | Suppléant de | Relu par |
|---|---|---|---|---|
| Oumayma Ennamous | Infrastructure KVM, automatisation, intégration | Inventaire des machines, réseau et VM (libvirt, cloud-init), Ansible, architecture, Secrets, ADR-000, intégration MLflow | Thanh Tu | Thanh Tu |
| Thanh Tu Vo | Kubernetes, stockage et chaîne ML | K3s, Longhorn, PostgreSQL et MinIO, MLflow, `train.py`, expériences et registre, Jobs d'entraînement, ADR-001 et ADR-002 | Marwa | Oumayma |
| Marwa Boumour | Observabilité et mesures | ADR-003, Prometheus et Grafana, dashboards et alertes, protocole et analyse de mesures | Oumayma | Oumayma et Thanh Tu |
| Tous | Reproductibilité et soutenance | Journaux, carnets individuels, preuves, rapport, démo, revue des décisions | n/a | Revue croisée |

Le suppléant relit le travail du pilote et doit pouvoir le remplacer : tout membre peut être interrogé sur toute l'architecture (oral du 20/11).

Le laboratoire VMware d'Oumayma et le POC MLflow de Thanh Tu sont des acquis à transférer, pas une raison de considérer le travail des autres comme terminé. L'intégration exige des tests communs. Les rôles peuvent être rééquilibrés après un jalon selon la charge réelle ; tout changement est noté dans le journal.

## 2. Règles de travail

- Point d'équipe de 15 min au début de chaque créneau ; 5 lignes dans `docs/journal/AAAA-MM-JJ.md` (fait, bloqué, prévu).
- Relecture croisée : toute modification de script ou de manifeste est relue par un autre membre avant fusion dans `main`.
- Règle des 3 heures : bloqué plus de 3 h effectives, on demande de l'aide à l'équipe ; bloqué plus d'un créneau sur une étape critique, on applique le plan B de l'ADR concerné et on le note dans le journal.
- Un jalon est validé par un tag Git (`jN`) posé sur `main` et par une checklist avec preuves dans `docs/jalons/` ; point sans preuve = non validé.
- Carnet de bord individuel : 3 à 5 lignes par semaine (heures, tâches, difficultés).
- Aucun secret dans Git ; tout est reconstructible par script depuis le dépôt.
- Les dates et critères ci-dessous ne valent pas validation du professeur.

## 3. Jalons et critères d'acceptation

| Échéance | Travail | Acceptation et preuves |
|---|---|---|
| **J1, ven. 06/11, 18:00** | Architecture courte et schéma, ADR, risques, rôles ; revue | Liens de la checklist vérifiés, décisions revues, tag `j1` posé sur `main` après revue |
| **J2, ven. 20/11, 18:00** | VM KVM, K3s, Longhorn, PostgreSQL et MinIO ; automatisation | Installation sur la cible reconstructible par script, réseau stable, données conservées après recréation des pods ; oral J1/J2 le matin |
| **J3, mar. 15/12, 18:00** | MLflow sur le cluster, plusieurs entraînements, comparaison, registre et promotion | Runs reproductibles, métriques, artefacts téléchargeables, version promue (alias `champion`) avec justification ; Go/No-Go |
| **Rédaction, ven. 18/12** | Sections J1 à J3 du rapport ; sauvegarde avant les vacances | Rapport en cours, restauration documentée |
| **J4, ven. 22/01, 18:00** | Job ou CI, hyperparamètres, analyse, observabilité | Protocole fixé avant les essais, au moins 3 répétitions, médiane et dispersion, résultats bruts ; alertes testées |
| **Gel, ven. 29/01** | Stabilisation | Aucune nouvelle fonctionnalité |
| **J5, ven. 05/02, 18:00** | Destruction puis reconstruction | Exécution chronométrée et filmée par un membre qui ne l'a jamais faite |
| **Rendu final, ven. 12/02, 18:00** | Rapport, dépôt, `make demo` | Démo scriptée ; soutenance entre le 8 et le 19/02 selon convocation |

KServe et Streamlit : après J3 uniquement si le cœur est validé et que la capacité le permet. Prometheus et Grafana sont préparés en parallèle sans bloquer J2.

## 4. Plan détaillé jusqu'à J2

| Période | Oumayma (infra) | Thanh Tu (K8s, ML) | Marwa (observabilité) |
|---|---|---|---|
| 04–05/11 | ADR-000, architecture V3, inventaire des machines | ADR-001 et ADR-002 (fusion), plan de travail, README, `versions.yaml`, POC MLflow | ADR-003, risques d'observabilité |
| 05/11 soir | relecture croisée, revue des liens | idem | idem |
| 06/11 | checklist J1 et preuves ensemble, journaux, carnets, fusion dans `main`, tag `j1` avant 18:00 | idem | idem |
| 07–13/11 | VM KVM/libvirt avec cloud-init, réseau, accès SSH | scripts d'installation K3s, manifestes Longhorn, PostgreSQL et MinIO, testés en local ou sur les VM | prototype Prometheus et Grafana en local, liste des métriques et alertes |
| 14–19/11 | reconstruction par script, vérification de la reconstruction par un autre membre | K3s, Longhorn, PostgreSQL et MinIO, persistance après recréation des pods | premières métriques du cluster |
| 20/11 | oral le matin ; tag `j2` avant 18:00 | idem | idem |

Date limite de bascule vers le plan B du socle ou du stockage : à fixer dans ADR-000 et ADR-002 (par exemple `local-path` à la place de Longhorn si les ressources ne suffisent pas). Ces plans B sont prévus dans les ADR ; la date de déclenchement reste à fixer ensemble.

## 5. Après J2

| Jalon | Oumayma | Thanh Tu | Marwa |
|---|---|---|---|
| J3 (15/12) | support infra, sauvegardes, Secrets | MLflow sur le cluster, au moins 2 familles d'algorithmes, runs comparés (Telco Churn), alias `champion` | dashboards, premières alertes |
| J4 (22/01) | automatisation, CI | Job Kubernetes, recherche d'hyperparamètres, analyse | protocole de mesure, pannes contrôlées, coût de l'observabilité |
| J5 (05/02) | scripts de reconstruction | idem | idem ; la reconstruction est faite par un membre qui n'a jamais installé la partie concernée |
| Rendu (12/02) | rapport, `make demo` | rapport, soutenance | rapport, soutenance |

## 6. Dépendances et prochaines actions

1. Inventorier les machines physiques et confirmer socle, réseau et ressources (Oumayma, avant l'implémentation sur la cible).
2. Relire les quatre ADR, les risques et les rôles (groupe, avant la clôture de J1).
3. Importer les manifestes du POC, vérifier les Secrets et les versions (Oumayma et Thanh Tu, avant J2).
4. Automatiser VM, K3s, stockage, services, et essayer depuis une cible vierge (Oumayma et Thanh Tu, J2).
5. Verser les preuves de persistance et vérifier les volumes applicatifs (Thanh Tu, J2).
6. Consolider les runs réels, registre et promotion, sans sélection sur le jeu de test (Thanh Tu avec Oumayma, J3).
7. Construire l'image d'entraînement, exécuter les Jobs et la recherche d'hyperparamètres, mesurer (Thanh Tu et Marwa, J4).
8. Préparer la restauration et organiser une reconstruction croisée avant le gel (tous).

## 7. Reconstruction visée : outils à implémenter

| Étape | Outil envisagé | État dans cette branche au cadrage |
|---|---|---|
| Création des VM et du réseau | libvirt, cloud-init, scripts idempotents | À implémenter |
| Configuration des VM et de K3s | Ansible | À implémenter |
| Stockage et applications | Manifestes ou Helm avec versions figées | À importer du POC, relire et tester |
| Entraînement | Script Python, puis image et Job Kubernetes | train.py housing et churn (baseline, jeu de test) ; pipeline complète, validation et Job à livrer |
| Exploitation et preuves | Scripts, checklists et `make demo` | À implémenter |

Cette liste annonce des livrables ; elle ne fournit pas de commandes supposées déjà opérationnelles.

## 8. Rituels et suivi

- Revue du plan à la fin de chaque jalon (rééquilibrage des rôles si besoin).
- Créneaux officiels : [à confirmer dans l'emploi du temps] ; hors créneaux, travail sur temps libre.
- Canal de communication : [à préciser] ; décisions importantes reportées dans le journal ou dans un ADR.