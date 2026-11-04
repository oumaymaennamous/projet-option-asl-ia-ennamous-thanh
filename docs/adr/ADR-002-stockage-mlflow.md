# ADR-002 — PostgreSQL, MinIO et volumes Longhorn

- Date : 4 novembre 2026.
- Statut : architecture retenue pour le POC ; validation et reconstruction sur KVM à réaliser.

## Contexte

J2 exige PostgreSQL et MinIO avec stockage persistant. J3 exige un serveur MLflow et un registre. Les données doivent survivre au remplacement d’un pod ; la reprise sur un autre nœud est un objectif complémentaire.

## Options comparées

| Option | Avantages | Limites |
|---|---|---|
| PostgreSQL + MinIO | Sépare SQL et objets S3 ; conforme au sujet | Deux services à exploiter et sauvegarder |
| SQLite + fichiers locaux | Très simple pour un essai | Ne remplit pas la cible J2 PostgreSQL/MinIO ; dépendance locale |
| PostgreSQL + stockage objet externe | Externalise une partie de l’exploitation | Dépendances réseau/coût/accès ; moins autonome |

Pour les volumes : `local-path` est simple mais lié au nœud ; Longhorn permet la réplication et un rattachement sur un autre nœud au prix de ressources, d’espace et d’exploitation supplémentaires. NFS externe est une alternative mais son serveur devient critique sans redondance propre.

## Décision

- MLflow stocke les métadonnées, expériences et registre dans PostgreSQL.
- MLflow transfère les modèles/artefacts vers le bucket MinIO `mlflow-artifacts` en mode proxy.
- Un StatefulSet initial pour PostgreSQL et un pour MinIO, une instance chacun, Services internes.
- PVC distincts, classe `longhorn-3copies` : `numberOfReplicas: 3`, anti-affinité des réplicas par nœud stricte, `Retain`, expansion autorisée, moteur V1.
- Le POC utilise 2 Gio par PVC ; dimensionnement final après mesure. `ReadWriteOnce` ne signifie pas une seule copie de stockage.

`/data` dans MinIO est un montage du volume, pas une copie indépendante dans le conteneur. La réplication Longhorn ne réplique pas automatiquement PostgreSQL au niveau SQL. La reprise peut être interrompue.

## Plan B

Si Longhorn empêche durablement J2 faute de capacité ou de compatibilité, conserver PostgreSQL/MinIO avec PVC local-path et sauvegardes hors hôte, en assumant l’indisponibilité si le nœud portant le volume tombe. Une migration ultérieure exige copie/restauration des données et vérification ; changer la StorageClass par défaut ne migre pas les PVC existants.

MinIO communautaire : les images et binaires publics ont échoué dans le laboratoire (401/410). Une image a été construite depuis un tag source. Conserver source, commit, recette, dépendances, archive/digest et accès sur tous les nœuds. Si une reconstruction maintenable devient impossible, rechercher une solution S3 maintenue ou un fork vérifié et demander validation du changement au regard du brief exigeant MinIO. Aucun miroir inconnu ni `latest` non contrôlé.

## Sauvegardes et validation

Sauvegarder PostgreSQL de façon cohérente (ex. pg_dump pour la petite base), objets/configuration MinIO et identifiants via une procédure sécurisée, sur une cible indépendante. Les snapshots Longhorn ne suffisent pas. Tester la restauration.

POC déclaré : données SQL et objet S3 retrouvés après recréation du pod ; trois copies actives vérifiées pour un volume de test. À verser : preuves SQL/S3, santé et placement des réplicas des **volumes applicatifs**, test de reprise contrôlé et restauration. Ne pas forcer un détachement avant d’avoir confirmé l’arrêt de l’ancien écrivain.
