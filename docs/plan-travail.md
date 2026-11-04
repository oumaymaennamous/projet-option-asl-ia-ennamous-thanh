# Plan de travail et rôles — J1

Établi le 4 novembre 2026. **Répartition proposée**, sans présumer d’une validation ou de travaux déjà réalisés par les autres membres. Équipe indiquée dans le journal du 23 octobre : Oumayma Ennamous, Thanh Tu Vo, Marwa Boumour.

## Responsabilités et relectures

| Membre | Responsabilité principale proposée | Livrables | Relecture proposée |
|---|---|---|---|
| Oumayma | Infrastructure KVM, automatisation et intégration | Inventaire, réseau/VM, Ansible, architecture, Secrets, intégration MLflow et extensions | Thanh Tu |
| Thanh Tu | Kubernetes, stockage et chaîne ML | K3s, Longhorn, PostgreSQL/MinIO, expériences/registre et Job d’entraînement | Oumayma |
| Marwa | Observabilité et mesures | ADR-003, collecte, dashboards/alertes, protocole et analyse de mesures | Oumayma et Thanh Tu |
| Tous | Reproductibilité et soutenance | Journaux, carnets individuels, preuves, rapport, démo et revue des décisions | Revue croisée |

Le POC personnel d’Oumayma est un acquis à transférer, pas une raison de considérer le travail d’un autre membre comme terminé. L’intégration exige des tests communs. Réviser la répartition selon la charge réelle.

## Jalons et critères d’acceptation

| Échéance du brief | Travail | Acceptation et preuves |
|---|---|---|
| **J1 — 6/11/2026, 18 h** | Architecture courte et schémas, ADR, risques, rôles ; revue | Liens de la checklist vérifiés, décisions revues, document court mis en forme, tag après revue |
| **J2 — 20/11/2026, 18 h** | KVM/VM, K3s, Longhorn, PostgreSQL et MinIO ; automatisation | Installation sur cible reconstructible, réseau stable et données conservées après recréation ; oral le matin |
| **J3 — 15/12/2026, 18 h** | MLflow, plusieurs entraînements, comparaison, registre et promotion | Runs reproductibles, métriques, artefacts téléchargeables et version promue avec justification |
| **Rédaction — 18/12/2026** | Sections J1–J3 et sauvegarde avant vacances | Rapport en cours et restauration documentée |
| **J4 — 22/01/2027, 18 h** | Job/CI, hyperparamètres, analyse et observabilité | Protocole fixé avant essais, ≥3 répétitions, médiane et dispersion, résultats bruts ; alertes testées |
| **Gel — 29/01/2027** | Stabilisation | Aucune nouvelle fonctionnalité |
| **J5 — 5/02/2027, 18 h** | Détruire puis reconstruire | Exécution chronométrée et filmée par un membre qui ne l’a jamais faite |
| **Final — 12/02/2027, 18 h** | Rapport, dépôt et `make demo` | Démo scriptée ; soutenance entre 8 et 19 février selon convocation |

KServe/Streamlit : après J3 uniquement si le cœur est validé et que la capacité le permet. Prometheus/Grafana sont préparés en parallèle sans bloquer J2. Ni les dates ni les critères ne sont une déclaration de validation du professeur.

## Dépendances et prochaines actions

1. Inventorier les machines physiques et confirmer le socle, le réseau et les ressources — Oumayma, avant implémentation cible.
2. Relire les quatre ADR, les risques et les rôles — groupe, avant clôture J1.
3. Importer les scripts/manifests du POC, vérifier les Secrets et les versions — Oumayma/Thanh Tu, avant J2.
4. Automatiser VM → K3s → stockage → services et essayer depuis une cible vierge — Oumayma/Thanh Tu, J2.
5. Verser les preuves de persistance et vérifier les volumes applicatifs — Thanh Tu, J2.
6. Consolider les runs réels, registre et promotion, sans sélection sur le test — Thanh Tu avec Oumayma, J3.
7. Construire l’image d’entraînement, exécuter les Jobs et HPO, mesurer — Thanh Tu et Marwa, J4.
8. Préparer la restauration et organiser une reconstruction croisée avant le gel — tous.

## Reconstruction visée : outils à implémenter

| Étape | Outil envisagé | État dans cette branche au cadrage |
|---|---|---|
| Création VM et réseau | libvirt, cloud-init, scripts idempotents | À implémenter |
| Configuration VM et K3s | Ansible | À implémenter |
| Stockage et applications | Manifests/Helm avec versions figées | À importer du POC, relire et tester |
| Entraînement | Script Python puis image et Job Kubernetes | Notebook adapté ; script/Job à livrer |
| Exploitation et preuves | Scripts, checklists et `make demo` | À implémenter |

Cette liste annonce des livrables ; elle ne fournit pas de commandes fictives supposées déjà opérationnelles.
