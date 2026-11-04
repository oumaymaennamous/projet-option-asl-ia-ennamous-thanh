# ADR-001 — Distribution Kubernetes : k3s vs kubeadm

- Date : 2026-11-04
- Statut : proposé (à valider par Oumayma et Marwa)
- Auteur : Thanh Tu Vo

## Contexte
Le sujet 4 demande un cluster Kubernetes (« k3s suffit ») pour héberger MLflow, PostgreSQL, MinIO et les Jobs d'entraînement. Le socle visé est OpenStack all-in-one avec 2 VM (k3s-server et k3s-worker), voir l'architecture V2. La RAM de l'hôte est partagée entre OpenStack, les 2 VM, la stack MLOps et l'observabilité : RAM de l'hôte = [à vérifier]. J2 (20/11) exige un cluster reconstructible par script.

## Options comparées

### Option 1 — k3s
- Installation par un script officiel, binaire unique
- Fournit par défaut Traefik, local-path-provisioner et metrics-server, utiles pour J2, J3 et l'observabilité
- Empreinte mémoire plus faible qu'un cluster kubeadm de base (ordre de grandeur à mesurer sur nos VM : [valeurs])
- Explicitement accepté par le sujet
- Moins proche d'un cluster « standard » (composants embarqués)
- Datastore par défaut (SQLite) adapté à un seul serveur, pas à la HA

### Option 2 — kubeadm
- Distribution de référence, composants séparés, bon pour apprendre
- Pas de composants imposés (CNI, ingress, stockage au choix)
- Il faut installer et choisir soi-même runtime, CNI, StorageClass, ingress et metrics-server
- Empreinte mémoire et temps d'installation plus élevés (à mesurer : [valeurs])
- Plus de scripts à maintenir pour J2 et J5

## Décision
k3s pour le cluster principal (1 serveur + 1 worker).

Justification :
1. Accepté par le sujet.
2. Moins de composants à installer et à maintenir, donc une
   reconstruction par script plus simple (J2, J5).
3. Les addons inclus couvrent nos besoins initiaux.
4. La RAM de l'hôte est partagée avec OpenStack ; k3s limite la
   consommation du cluster.

## Conséquences
- StorageClass `local-path` : volumes attachés à un nœud. Les pods PostgreSQL et MinIO sont épinglés sur le worker (nodeSelector); sauvegardes hors VM à prévoir.
- Ingress : Traefik fourni par k3s.
- metrics-server fourni, utile pour `kubectl top` et les mesures J4.
- Version exacte de k3s figée dans `versions.yaml` : [à vérifier].
- Installation scriptée (Ansible ou shell versionné), documentée dans `docs/installation/k3s.md`.

## Plan B
Déclencheur : si le cluster k3s n'est pas fonctionnel (nœuds Ready, DNS OK, PVC testé) le [date, ex. 18/11] à cause de k3s lui-même.
Action : kubeadm + CNI + ingress-nginx + local-path-provisioner, testé d'abord sur un cluster local. Le changement est documenté par un avenant à cet ADR et noté dans le journal.