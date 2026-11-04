# ADR-000 — KVM/libvirt plutôt qu’OpenStack

- Date : 4 novembre 2026.
- Statut : choix proposé par Oumayma pour J1, à confirmer en groupe après inventaire.
- Remplace l’orientation OpenStack all-in-one de la V2 pour l’architecture courante ; conserve l’historique.

## Contexte

Le brief autorise OpenStack all-in-one avec Kolla-Ansible **ou** VM KVM/libvirt. Le sujet est le MLOps et non la construction d’un cloud. La capacité des machines physiques n’a pas encore été inventoriée dans cette branche. Le POC est sous VMware sur le poste personnel.

## Comparaison

| Critère | KVM/libvirt | OpenStack all-in-one |
|---|---|---|
| Fonction | Exécuter et gérer directement les VM | Fournir des API de cloud et services réseau/images/identité |
| Ressources et exploitation | Moins de services intermédiaires | Davantage de services et de dépendances |
| Automatisation | cloud-init, libvirt et Ansible | Kolla-Ansible puis API/OpenTofu |
| Pertinence pour le sujet 4 | Suffisant pour héberger K3s | Valide mais augmente le travail de socle |

OpenStack peut lui-même utiliser KVM : les deux options comparent des couches de gestion, pas deux moteurs nécessairement concurrents.

## Décision et conséquences

Retenir Ubuntu + QEMU/KVM + libvirt et automatiser la création/configuration des VM. Réserver d’abord les ressources de l’hôte. Renoncer aux fonctions de cloud inutiles au MVP, mais documenter réseau, IP, volumes et images explicitement. VMware reste le POC ; il n’est pas présenté comme le socle final autorisé.

## Plan B et déclenchement

Si l’hôte ne supporte pas les extensions de virtualisation ou que KVM est interdit/inaccessible, utiliser une autre machine compatible puis réévaluer avec l’enseignant. OpenStack n’est pas un secours pour un manque de RAM : le retenir seulement si un besoin de cloud et les ressources le justifient. Si la capacité empêche trois VM, activer le mode dégradé de l’ADR-001 et documenter la perte de HA.

## Validation à produire

Inventaire CPU/RAM/SSD, support matériel KVM, démarrage automatisé de VM, connectivité et reconstruction à partir de l’image Ubuntu. Aucun de ces résultats n’est affirmé comme validé sur le futur hôte.
