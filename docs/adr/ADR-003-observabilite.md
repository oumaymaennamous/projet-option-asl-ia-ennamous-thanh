# ADR-003 — Mise en place de l’observabilité avec Prometheus, Grafana et Loki

- **Date :** 6 novembre 2026
- **Statut :** Décision proposée pour J1, à valider par le groupe. Déploiement et validation prévus lors des jalons suivants.
- **Responsable :** Marwa Boumour
- **Périmètre :** Supervision de la plateforme MLOps : cluster K3s, MLflow, PostgreSQL, MinIO et jobs d’entraînement.

## 1. Contexte

La plateforme MLOps doit permettre de suivre l’exécution des expériences MLflow, le stockage des métadonnées dans PostgreSQL, le stockage des artefacts dans MinIO ainsi que les jobs d’entraînement exécutés sur Kubernetes.

Le bon fonctionnement de ces composants ne suffit pas à garantir la disponibilité et les performances de la plateforme. Il est également nécessaire de pouvoir détecter les problèmes, comprendre leur origine et suivre l’évolution de l’utilisation des ressources.

L’observabilité doit donc répondre à trois besoins :

- **Métriques :** connaître l’état et les performances des composants (CPU, mémoire, disponibilité, utilisation du stockage, erreurs, durée des jobs, etc.).
- **Logs :** consulter les événements et les erreurs produits par les applications et les composants Kubernetes afin de faciliter le diagnostic.
- **Alertes :** être informé lorsqu’un composant devient indisponible, qu’une ressource approche de sa limite ou qu’un job échoue.

Cette observabilité doit couvrir progressivement les composants de la plateforme et permettre de réaliser des mesures de performance pour le jalon J4.

## 2. Objectifs et besoins

La solution retenue doit permettre de :

1. Surveiller l’état des nœuds K3s et des pods.
2. Suivre les ressources CPU, mémoire et disque utilisées par les machines et les conteneurs.
3. Surveiller la disponibilité et les performances de MLflow, PostgreSQL et MinIO.
4. Suivre l’état des jobs Kubernetes : en cours, terminés ou en échec, ainsi que leur durée d’exécution.
5. Centraliser les logs utiles au diagnostic des incidents.
6. Construire des tableaux de bord permettant de visualiser l’état général de la plateforme.
7. Définir des alertes et vérifier leur fonctionnement en provoquant des incidents contrôlés.
8. Collecter des mesures exploitables pour analyser les performances de la plateforme au jalon J4.

Les métriques liées à la qualité des modèles (accuracy, precision, recall, F1-score, etc.) restent suivies dans MLflow. Elles ne doivent pas être confondues avec les métriques techniques de supervision de l’infrastructure.

## 3. Options étudiées

### 3.1. Solutions de collecte et de visualisation des métriques

| Solution | Avantages | Limites |
|---|---|---|
| Prometheus + Grafana | Collecte des métriques, requêtes temporelles, tableaux de bord et intégration avec Kubernetes | Configuration des cibles de collecte et consommation de ressources |
| Zabbix | Supervision de serveurs, équipements et services avec alertes intégrées | Moins adapté à une supervision centrée sur les métriques Kubernetes et les workloads conteneurisés |
| Outils de monitoring cloud | Services managés et exploitation simplifiée | Dépendance à un fournisseur externe et moins d'autonomie pour un laboratoire local |

### 3.2. Solutions de centralisation des logs

| Solution | Avantages | Limites |
|---|---|---|
| Loki + Alloy | Centralisation des logs, intégration avec Grafana et collecte depuis Kubernetes | Consommation de ressources et configuration supplémentaire |
| Elasticsearch + Logstash + Kibana (ELK) | Recherche et analyse avancées des logs | Stack plus lourde à déployer et à maintenir |
| Logs Kubernetes avec kubectl | Solution simple, disponible directement dans le cluster | Consultation principalement manuelle, sans centralisation ni historique global |

### 3.3. Solutions de gestion des alertes

| Solution | Avantages | Limites |
|---|---|---|
| Alertmanager | Intégration avec Prometheus, regroupement et gestion des alertes | Nécessite de définir et configurer les règles d'alerte |
| Alertes Grafana | Configuration directement depuis Grafana | Gestion moins centralisée si plusieurs sources de métriques sont utilisées |

## 4. Décision

Retenir une architecture d’observabilité basée sur les composants suivants :

- **Prometheus :** collecte et conserve les métriques techniques de la plateforme à partir de différentes cibles de supervision.
- **Grafana :** visualise les métriques sous forme de tableaux de bord et permet de suivre l’état des différents composants.
- **Alertmanager :** reçoit les alertes générées par Prometheus, les regroupe et gère leur transmission selon les règles définies.
- **Loki :** centralise les logs des applications et des composants Kubernetes.
- **Alloy :** collecte et transmet les logs vers Loki.

Prometheus, Grafana et Alertmanager constituent le socle principal de supervision. Loki et Alloy seront intégrés si les ressources disponibles sur les trois VM le permettent.

Cette décision privilégie des outils open source, adaptés à Kubernetes et intégrables dans une architecture locale sans dépendre d’un service cloud externe.

### 4.1. Architecture fonctionnelle

Les composants de supervision seront déployés dans le namespace Kubernetes `monitoring`, séparé du namespace applicatif `mlops`.

Le fonctionnement prévu est le suivant :

- Prometheus collecte périodiquement les métriques exposées par les composants et les exporters.
- Grafana interroge Prometheus pour afficher les tableaux de bord.
- Prometheus évalue les règles d'alerte et transmet les alertes déclenchées à Alertmanager.
- Alloy collecte les logs des pods et les transmet à Loki.
- Grafana permet de consulter les logs centralisés dans Loki, en complément des métriques.

### 4.2. Sources de métriques prévues

| Composant surveillé | Données recherchées | Moyen de collecte envisagé |
|---|---|---|
| Nœuds K3s | CPU, mémoire, disque, disponibilité | Node Exporter et métriques du nœud |
| Kubernetes | État des pods, redémarrages, ressources demandées et utilisées | Kube-state-metrics et métriques du cluster |
| MLflow | Disponibilité du serveur, erreurs et temps de réponse | Vérification HTTP et métriques applicatives si disponibles |
| PostgreSQL | Connexions, disponibilité, activité et utilisation de la base | PostgreSQL Exporter |
| MinIO | Disponibilité, capacité de stockage et activité | Endpoint de métriques MinIO |
| Jobs d'entraînement | État des jobs, durée, succès et échecs | État des ressources Kubernetes et métriques des workloads |

Les métriques effectivement exposées par chaque composant devront être vérifiées pendant l'intégration. En particulier, la disponibilité d'un endpoint Prometheus natif pour MLflow ne sera pas supposée : si nécessaire, sa disponibilité sera suivie par des sondes HTTP et ses ressources par les métriques Kubernetes.

Les métriques de qualité des modèles resteront consultables dans MLflow.

### 4.3. Tableaux de bord prévus

Les tableaux de bord Grafana seront organisés autour de trois vues :

- **Vue infrastructure :** état des nœuds, CPU, mémoire, disque et ressources Kubernetes.
- **Vue services MLOps :** disponibilité de MLflow, PostgreSQL et MinIO, état des pods et indicateurs de fonctionnement.
- **Vue entraînement :** nombre de jobs exécutés, jobs en échec, durée des entraînements et consommation des ressources associées.

Ces tableaux de bord seront construits progressivement à partir des métriques réellement disponibles.

### 4.4. Alertes prévues

Les règles d'alerte seront définies dans Prometheus et transmises à Alertmanager.

Les premiers cas à couvrir sont :

| Situation | Condition envisagée | Objectif |
|---|---|---|
| Nœud indisponible | Cible de collecte inaccessible | Détecter une panne de nœud |
| Pod en échec | Pod en état `CrashLoopBackOff` ou échec persistant | Identifier un service qui ne démarre pas correctement |
| Utilisation CPU ou mémoire élevée | Dépassement d'un seuil défini pendant une durée donnée | Anticiper une saturation des ressources |
| PostgreSQL indisponible | Exporter ou vérification de disponibilité en échec | Détecter une indisponibilité de la base |
| MinIO indisponible | Endpoint de supervision inaccessible | Détecter un problème de stockage objet |
| Job d'entraînement en échec | Job Kubernetes en état `Failed` | Identifier un entraînement interrompu |

Les seuils exacts seront définis après les premières mesures du laboratoire. Ils ne sont donc pas considérés comme fixés à ce stade.

## 5. Conséquences de la décision

### Avantages

- Disposer d'une vision centralisée de l'état de la plateforme MLOps.
- Détecter plus rapidement les problèmes d'infrastructure et de disponibilité des services.
- Faciliter le diagnostic grâce à la consultation des métriques et des logs.
- Suivre les ressources consommées par les entraînements.
- Produire des mesures objectives pour l'analyse des performances au jalon J4.
- Utiliser une solution open source adaptée à un environnement Kubernetes.

### Contraintes et limites

- Les composants de monitoring consomment eux-mêmes des ressources CPU, mémoire et stockage.
- La configuration des exporters et des règles d'alerte demande un travail supplémentaire.
- Les métriques disponibles dépendent des interfaces exposées par les composants.
- La centralisation des logs augmente les besoins de stockage.
- Une panne de l'hôte physique peut interrompre à la fois la plateforme MLOps et son système de supervision.
- La supervision ne garantit pas à elle seule la sauvegarde ou la restauration des données.

## 6. Plan B et conditions de déclenchement

Si le déploiement complet de la stack d'observabilité dépasse les ressources disponibles ou compromet le fonctionnement des composants MLOps prioritaires, une version réduite sera utilisée.

Le plan de repli prévoit :

- Conserver Prometheus et Grafana pour la collecte et la visualisation des métriques essentielles.
- Réduire le nombre de cibles de collecte et la fréquence de collecte si nécessaire.
- Reporter Loki et Alloy à une étape ultérieure et utiliser temporairement `kubectl logs` pour consulter les logs.
- Réduire la durée de conservation des métriques si l'espace disque devient insuffisant.
- Conserver un ensemble limité d'alertes prioritaires sur la disponibilité des nœuds et des services.

Le déclenchement du mode dégradé sera décidé à partir des mesures réelles de consommation CPU, mémoire et disque sur les VM.

Le retrait de Loki et Alloy ne devra pas supprimer la capacité de consulter les logs nécessaires au diagnostic des incidents.

## 7. Vérifications et critères de validation

La décision sera considérée comme validée après les vérifications suivantes :

1. Prometheus est déployé et accessible dans le namespace `monitoring`.
2. Prometheus collecte correctement les métriques des nœuds et des composants configurés.
3. Grafana est accessible et affiche les données collectées par Prometheus.
4. Les tableaux de bord présentent les indicateurs principaux de l'infrastructure et des services MLOps.
5. Les règles d'alerte sont configurées et leur déclenchement est vérifié.
6. Alertmanager reçoit correctement les alertes générées.
7. Si Loki et Alloy sont déployés, les logs des composants ciblés sont consultables depuis Grafana.
8. Des incidents contrôlés sont provoqués afin de vérifier la détection et le diagnostic : arrêt contrôlé d'un service, indisponibilité d'une cible de collecte ou échec d'un job de test.
9. Les mesures de consommation des ressources et de durée des jobs sont conservées pour l'analyse de performance du jalon J4.

Les tests devront être réalisés de manière contrôlée, sans mettre en danger les données persistantes de PostgreSQL et MinIO.

Aucun de ces critères ne sera déclaré validé avant la réalisation des tests et le dépôt des preuves correspondantes.

## 8. Planification

| Jalon | Travail lié à l'observabilité |
|---|---|
| J1 — 06/11/2026 | Définir l'architecture, les outils, les métriques à suivre, les alertes et les risques |
| J2 — 20/11/2026 | Préparer l'intégration de la supervision avec le cluster et les services de stockage |
| J3 — 15/12/2026 | Déployer la stack principale et construire les premiers tableaux de bord |
| J4 — 22/01/2027 | Tester les alertes, provoquer des incidents contrôlés et mesurer les performances de la plateforme |
| J5 — 05/02/2027 | Finaliser les vérifications, les preuves et la documentation |

## 9. Risques identifiés

| Risque | Conséquence possible | Mesure de réduction |
|---|---|---|
| R1 — Ressources insuffisantes | Dégradation des performances de K3s ou des services MLOps | Mesurer la consommation et utiliser le mode dégradé |
| R2 — Métriques non exposées | Supervision incomplète de certains composants | Vérifier les endpoints et utiliser des exporters ou des sondes adaptés |
| R3 — Accumulation des métriques et des logs | Saturation du stockage | Définir une durée de rétention et surveiller l'espace disque |
| R4 — Mauvaise configuration des alertes | Alertes absentes ou trop nombreuses | Tester les règles avec des incidents contrôlés et ajuster les seuils |
| R5 — Panne de l'hôte physique | Arrêt de la plateforme et de la supervision | Documenter cette limite et conserver les procédures de diagnostic et de restauration |

## 10. Conclusion

Le choix de Prometheus, Grafana et Alertmanager fournit un socle cohérent pour superviser les ressources et les services de la plateforme MLOps. Loki et Alloy complètent cette architecture en permettant la centralisation des logs, sous réserve du budget de ressources disponible.

Cette architecture doit permettre de détecter les incidents, de faciliter leur diagnostic et de disposer de mesures fiables pour évaluer les performances de la plateforme au jalon J4.

La validation définitive dépendra des tests réalisés sur le cluster K3s cible et de l'inventaire réel des ressources disponibles.