# J1 — Cadrage : checklist et preuves

**Échéance : 6 novembre 2026, 18 h.** Préparation du 4 novembre sur `oumayma`. Cette checklist décrit l’état documentaire de ce commit ; elle n’est ni une approbation de l’équipe ni une validation du professeur.

## Livrables présents

- [x] Entrée de dépôt : [README](../../README.md).
- [x] Architecture actuelle KVM/libvirt, avec schéma : [Architecture générale J1](../architecture/architecture-v0.md).
- [x] Alternative socle et plan B : [ADR-000](../adr/ADR-000-socle-kvm-libvirt.md).
- [x] Distribution Kubernetes, alternative et plan B : [ADR-001](../adr/ADR-001-k3s-vs-kubeadm.md).
- [x] Stockage artefacts/base, alternatives et plan B : [ADR-002](../adr/ADR-002-stockage-mlflow.md).
- [x] Volet observabilité : [ADR-003](../adr/ADR-003-observabilite.md).
- [x] [Registre des risques](../risques.md).
- [x] [Planning et répartition proposée](../plan-travail.md).
- [x] [Journal de préparation documentaire](../journal/2026-11-04.md).
- [x] Preuves POC MLflow local (4 runs Housing + Churn) : [docs/jalons/preuves/](preuves/) — 7 captures.
- [x] POC `train.py` dual-dataset (housing + churn) versionné : [ml/src/train.py](../../ml/src/train.py).
- [x] `versions.yaml` avec versions testées.

## À terminer avant de déclarer J1 prêt

- [ ] Revue de l’architecture et acceptation des décisions/rôles par le groupe.
- [ ] Confirmer ressources physiques, support KVM, accès réseau et cible de sauvegarde ; noter les hypothèses restantes.
- [ ] Mettre en forme le document court en 2–3 pages et vérifier la lisibilité des schémas à l’export. Le Markdown n’a pas de pagination fixe.
- [ ] Vérifier l’accès de l’enseignant au dépôt et à la branche remise.
- [ ] Relire orthographe, liens, cohérence du statut réalisé/prévu et absence de secrets.
- [ ] Ajouter les preuves disponibles et le carnet individuel de chaque membre ; ne pas inventer présence ou résultats.
- [ ] Après revue seulement, créer le tag Git `j1` sur le commit retenu et conserver son SHA. Aucun tag de validation n’est créé automatiquement par ce document.

## Preuves à verser et emplacement proposé

Les preuves sont déposées dans `docs/jalons/preuves/` (déjà créé, 7 captures POC Housing + Churn). Les emplacements ci-dessous sont **des destinations prévues** pour les preuves futures, pas des fichiers existants :

| Preuve | Destination prévue | Usage |
|---|---|---|
| Inventaire hôte sans données sensibles | `docs/jalons/preuves/inventaire-hote.md` | Dimensionnement et ADR-000 |
| Compte rendu de revue de groupe | `docs/jalons/preuves/revue-j1.md` | Arbitrages et rôles |
| Architecture exportée et lisible | `docs/jalons/preuves/architecture-j1.pdf` | Document 2–3 pages |
| Trois nœuds et versions du POC | `docs/jalons/preuves/poc-k3s.txt` | Contexte, pas preuve de migration KVM |
| Recréation pods PostgreSQL/MinIO | `docs/jalons/preuves/persistance.md` | Préparation J2 |
| Runs et modèle retenu | `docs/jalons/preuves/mlflow.md` | Préparation J3 |

## Commandes de contrôle en lecture seule

À lancer depuis un environnement autorisé et à expurger avant publication :

```bash
sudo k3s kubectl get nodes -o wide
sudo k3s kubectl get pods,pvc,svc -n mlops
sudo k3s kubectl get nodes.longhorn.io -n longhorn-system
sudo k3s kubectl get volumes.longhorn.io -n longhorn-system
sudo k3s kubectl get replicas.longhorn.io -n longhorn-system
```

Ne pas publier kubeconfig, token K3s, Secrets Kubernetes, mots de passe, clés privées ni captures qui les affichent. La reproduction de commandes dans la documentation ne prouve pas leur résultat.
