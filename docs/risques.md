# Registre des risques

Statut : v0, à compléter par chaque pilote. Dernière mise à jour : 2026-11-04.

| # | Risque | Proba. | Impact | Signe d'alerte | Prévention | Plan B | Responsable |
|---|---|---|---|---|---|---|---|
| R1 | OpenStack all-in-one non fonctionnel avant J2 (20/11) | à évaluer | Élevé | `check` ou `prechecks` en échec ; aucune VM créée au [date] | Machine vérifiée tôt ; exécuter `check` dès l'accès | Basculer sur VM KVM/libvirt (ADR-000), date limite [à fixer] | Oumayma |
| R2 | Machine à une seule interface réseau : le script s'arrête | à évaluer | Élevé | `check` refuse la configuration | Vérifier les interfaces avant tout | Plan réseau spécifique ou KVM/libvirt | Oumayma |
| R3 | RAM insuffisante pour OpenStack + 2 VM + stack MLOps + monitoring | à évaluer | Élevé | OOM, VM lentes | Dimensionner après vérification de la machine | Une seule VM k3s ; Loki désactivé (Go/No-Go ADR-003) | Oumayma / Marwa |
| R4 | k3s non fonctionnel sur les VM (nœuds NotReady, DNS) | à évaluer | Moyen | Nœuds non Ready au [date, ADR-001] | Installation testée d'abord en local | kubeadm (ADR-001) | Thanh Tu |
| R5 | Perte d'un PVC (PostgreSQL ou MinIO) : runs ou artefacts perdus | à évaluer | Élevé | Pod redémarré sans données | Sauvegardes hors VM, restauration testée | Restauration depuis la sauvegarde ; SQLite + volume (ADR-002) | Thanh Tu |
| R6 | Migration SQLite vers PostgreSQL mal préparée | à évaluer | Moyen | Erreurs au démarrage de MLflow | Tester sur un cluster local avant J3 | Rester sur SQLite temporairement, documenté | Thanh Tu |
| R7 | Versions non figées : reconstruction non reproductible (J5) | à évaluer | Moyen | Résultat différent d'une installation à l'autre | `versions.yaml`, images et dépendances en cache | Cache local des dépendances et images | Tous |
| R8 | Secrets commités dans Git | à évaluer | Élevé | Mot de passe visible dans l'historique | `.gitignore`, relecture, Secrets Kubernetes | Révoquer et régénérer les secrets | Tous |
| R9 | Métriques et journaux saturent le stockage | à évaluer | Moyen | Disque du worker presque plein | Rétention bornée | Réduire la rétention, couper Loki | Marwa |
| R10 | Retard sur J2 qui décale tout le calendrier | à évaluer | Élevé | Tag j2 absent le lundi 23/11 matin | Avancer en parallèle (k3s en local, Prometheus en local) | Appliquer les plans B des ADR | Tous |
| R11 | Rôles non validés par tous | à évaluer | Moyen | Désaccord ou travail en double | Validation écrite du plan de travail | Rééquilibrer après J1 | Tous |

Les lignes R1 à R3 et R9 sont des propositions : Oumayma et Marwa doivent les relire et les compléter.