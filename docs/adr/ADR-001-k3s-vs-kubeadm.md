# ADR-001 — K3s plutôt que kubeadm

- Date : 4 novembre 2026.
- Statut : K3s validé dans le POC ; cible J1 proposée, validation physique restante.

## Contexte et comparaison

Le professeur autorise K3s. Il faut exploiter rapidement MLflow et ses stockages, comprendre Kubernetes et reconstruire le cluster.

| Critère | K3s | kubeadm |
|---|---|---|
| Nature | Distribution Kubernetes intégrée | Outil d’initialisation Kubernetes |
| Mise en place | Runtime et composants courants intégrés | Préparation du runtime et du réseau séparée |
| Exploitation du petit laboratoire | Plus simple à automatiser | Plus de choix et de configuration à maintenir |
| Apprentissage | Concepts Kubernetes conservés | Administration détaillée des composants |
| Multi-serveurs | etcd embarqué possible | Plan de contrôle HA configurable |

## Décision

K3s avec trois VM serveurs, etcd embarqué et noms/IP uniques. Même version et paramètres critiques sur tous les serveurs. Les serveurs accueillent aussi les pods, sans workers dédiés au départ. Les applications ne sont pas figées sur un nœud ; séparer leurs ressources par namespaces et requests/limits.

Cette topologie remplace l’ancienne proposition à un serveur et un worker. Trois membres etcd gardent un quorum de deux : une perte de membre tolérée, deux pertes bloquent la gestion. Une panne du seul hôte arrête tout.

## Alternative et plan B

kubeadm est le plan B si une incompatibilité K3s reproductible bloque une fonctionnalité obligatoire et ne peut être corrigée dans le délai du jalon. Figer les versions et valider le réseau/CSI sur la nouvelle distribution.

Si les ressources imposent un seul serveur K3s, le sujet 4 reste réalisable, mais la HA et trois copies Longhorn doivent être abandonnées ou adaptées explicitement. Ne pas présenter deux membres etcd comme une HA tolérant une panne.

## Vérifications et risques

POC : trois nœuds `Ready` déclarés/observés dans les échanges. À déposer : versions, sortie `kubectl get nodes -o wide`, test de perte d’un serveur et restauration, sans détruire les données. Prévoir snapshots etcd, protection du token et un point d’accès API stable. Le budget CPU/RAM et l’espace disque restent à confirmer sur la cible.
