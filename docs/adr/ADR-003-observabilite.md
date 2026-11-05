# ADR-003 — Prometheus et Grafana, collecte bornée

- Date : 4 novembre 2026.
- Statut : proposition de cadrage pour le volet de Marwa, implémentation à faire.

## Contexte et options

Le volet observabilité figure dans la V2 et le journal du groupe. Il complète le sujet 4. MLflow mesure les performances ML ; la supervision mesure la santé de la plateforme.

| Option | Utilité | Limites |
|---|---|---|
| Prometheus + Grafana + Alertmanager | Historique métriques, dashboards, alertes | CPU/RAM, stockage et rétention à maîtriser |
| metrics-server + kubectl/Headlamp | Diagnostic léger et immédiat | Pas d’historique/alertes équivalents |
| Loki + Alloy en supplément | Journaux centralisés corrélables | Charge et stockage additionnels |

## Décision

Namespace `monitoring` : Prometheus/Grafana et Alertmanager ; node-exporter, métriques kubelet et kube-state-metrics pour nœuds, conteneurs, pods/PVC/Jobs. Exporter PostgreSQL, métriques MinIO et sondes de disponibilité MLflow selon les possibilités des versions retenues. Ne pas supposer un endpoint natif universel MLflow.

Rétention initiale courte (par exemple 3 jours), tableaux de bord et règles versionnés, PVC bornés. Mesurer l’impact avant d’allonger la rétention. Journaux via `kubectl logs` au départ ; Loki/Alloy activés seulement si la charge et le stockage mesurés laissent une marge suffisante pour les entraînements et services.

## Plan B

Si les ressources manquent, conserver une collecte métrique réduite, diminuer cardinalité/rétention et renoncer d’abord à Loki. metrics-server/Headlamp et logs peuvent aider au diagnostic transitoire mais ne remplacent pas la preuve de dashboards/alertes attendue pour le volet observabilité : documenter l’écart et le replanifier.

## Preuves attendues

Dashboards CPU/RAM/disque, disponibilité et état des Jobs ; alerte sur service indisponible et Job échoué, puis résolution ; horodatages et sorties conservés. J4 : protocole fixé avant essais, au moins trois répétitions, valeurs brutes, médiane et dispersion. La supervision sur le même hôte disparaît lors de sa panne : les preuves/sauvegardes doivent sortir de cet hôte.
