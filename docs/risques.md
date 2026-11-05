# Registre des risques

Date : 4 novembre 2026. Échelles qualitatives : faible / moyenne / forte. Responsables proposés, à confirmer en groupe. Tous les risques sont ouverts tant que la preuve de maîtrise n'est pas déposée.

| ID | Risque / déclencheur | Probabilité | Impact | Prévention et plan B | Responsable proposé / preuve |
|---|---|---|---|---|---|
| R1 | RAM/CPU insuffisants pour trois VM et entraînements | Moyenne | Fort | Inventaire, réserves hôte, un Job à la fois, requests/limits ; réduire observabilité puis topologie en documentant la perte de HA | Oumayma ; inventaire et mesures |
| R2 | Panne de la machine physique unique | Moyenne | Fort | Sauvegardes externes et restauration ; répartir sur plusieurs hôtes si disponibles | Oumayma ; test restauration |
| R3 | Perte quorum etcd / panne de deux serveurs | Moyenne | Fort | Maintenance un nœud à la fois, santé vérifiée, snapshots et token protégé | Thanh Tu ; test panne et retour |
| R4 | Changement d'IP / point API dépendant d'une VM | Moyenne | Fort | MAC/IP stables, vérification DHCP/DNS ; point API redondant et certificats adaptés | Oumayma ; reboot et accès |
| R5 | Disques saturés / trois copies impossibles | Moyenne | Fort | Dimensionner Longhorn, disque données si possible, seuils et rétention ; local-path documenté en secours | Thanh Tu ; capacité et santé PVC |
| R6 | MinIO : image ou dépendance retirée / non maintenue | Forte | Fort | Source/tag/commit, image/digest conservés et reconstruction ; alternative S3 à valider avec l'enseignant | Thanh Tu ; build et pull sur nœud vierge |
| R7 | Suppression, corruption ou sauvegarde inutilisable | Moyenne | Fort | Sauvegardes SQL et objets hors hôte, restauration testée ; Retain n'est pas une sauvegarde | Thanh Tu ; exercice de restauration |
| R8 | Secrets dans Git ou interface exposée | Moyenne | Fort | Secrets hors dépôt, droits minimaux, accès privé, HTTPS avant exposition, contrôle des preuves | Oumayma ; revue et tests d'accès |
| R9 | Fuite de données ML / choix biaisé sur le test | Moyenne | Fort | Pipelines ajustées sur train, sélection sur validation, test final indépendant, graine/empreinte conservées | Thanh Tu ; notebook et runs |
| R10 | Modèle chargé sans bon prétraitement/seuil/dépendances | Moyenne | Fort | Sauvegarder pipeline complète, contrat d'entrée et versions ; test après rechargement | Thanh Tu ; prédictions identiques |
| R11 | KServe/Streamlit retardent le MVP obligatoire | Moyenne | Fort | Extensions après J3 ; runtime Standard ou prédicteur personnalisé ; geler extensions si J3 menacé | Oumayma ; checklist J3 |
| R12 | Observabilité consomme trop / ne voit pas panne hôte | Moyenne | Moyen | Rétention et labels bornés, Loki conditionnel, conservation des preuves hors hôte | Marwa ; mesures avec/sans collecte |
| R13 | Procédure manuelle impossible à reconstruire | Moyenne | Fort | Scripts et versions dans Git, essais sur VM vierge, revue croisée avant J5 | Tous ; reconstruction filmée |
| R14 | Formation/charge mal répartie ou indisponibilité membre | Moyenne | Moyen | Rôles et relecteurs, binômage, journal et carnet individuel ; réaffectation lors du point de groupe | Tous ; plan actualisé |
| R15 | Écart de versions entre client MLflow, serveur et chart Helm. Constaté au POC : MLflow 3.x refuse le stockage par fichiers et exige `skops_trusted_types` pour un RandomForest | Forte | Moyen | Versions client/serveur/chart alignées et figées dans `versions.yaml` ; test complet (run, enregistrement, rechargement) avant J3 ; sinon fixer `image.tag` | Thanh Tu ; `pip freeze` et run de bout en bout sur la version retenue |
| R16 | Migration SQLite vers PostgreSQL mal préparée : erreurs au démarrage de MLflow | Moyenne | Moyen | Tester sur un cluster local avant J3 ; secrets et URI vérifiés ; SQLite sur volume persistant en secours, limite documentée | Thanh Tu ; démarrage de MLflow sur PostgreSQL |
| R17 | Retard sur J2 qui décale tout le calendrier. Déclencheur : tag `j2` absent le lundi 23/11 au matin | Moyenne | Fort | Avancer en parallèle (K3s et Prometheus en local) ; appliquer les plans B des ADR ; noter le retard dans le journal | Tous ; état des preuves à J-3 |
| R18 | Rôles, relecteurs ou ADR non validés par tous : désaccord, travail en double | Moyenne | Moyen | Validation écrite du plan de travail et des ADR ; rééquilibrer après chaque jalon | Tous ; revue de J1 |
| R19 | Socle KVM/libvirt non confirmé : machines non inventoriées, virtualisation matérielle indisponible ou accès impossible | Moyenne | Fort | Inventaire et test KVM avant tout déploiement ; réduire le nombre de VM ; plan B à compléter dans ADR-000 | Oumayma ; inventaire et résultat du test |
| R20 | Jeu de données Telco Churn : source, licence ou version non documentées | Moyenne | Moyen | Documenter source, licence, version et empreinte ; conserver California Housing comme jeu de repli du POC | Thanh Tu ; fiche du jeu de données |

Révision : à chaque séance et avant chaque jalon. Ne clore un risque qu'avec une preuve référencée et la description du risque résiduel.