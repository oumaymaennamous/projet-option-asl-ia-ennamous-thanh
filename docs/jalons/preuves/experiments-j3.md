# J3 — Campagne d'expériences et sélection du champion

**Dates :** 23/11 (campagne initiale, v1) et 27/11 (rejeu, v2)
**Dataset :** Telco Customer Churn (sha256 `4cd901efab211ccb154051a93a1ab5e9298e37e8fd29bbf2c097da23cee36017`)
**Source :** `https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/master/data/Telco-Customer-Churn.csv`
**Licence :** Apache-2.0 est la licence du dépôt IBM (code pattern) ; licence propre aux données non établie (voir mlflow.md). Usage pédagogique.

## Setup

| Composant | Valeur |
|---|---|
| MLflow serveur | 3.18.0, image `ghcr.io/mlflow/mlflow:v3.18.0-full`, digest `sha256:a8459ca08b...` |
| MLflow client | 3.18.0 (venv Python 3.12.10, laptop via tunnel SSH) |
| Backend store | PostgreSQL 16, base `mlflow`, Secret `mlflow-db` |
| Artefact store | MinIO `mlflow-artifacts`, **mode proxy** (client sans credentials S3) |
| Cluster | K3s v1.37.2+k3s1, 3 serveurs sur n2 |
| Split | stratifié 60/20/20, `split_seed=42` |
| Seeds d'entraînement | 42, 123, 2026 |

## Protocole (conforme R9)

1. **Aucune sélection sur le test set.**
2. Famille gagnante = argmax **médiane `val_f1`** sur 3 seeds.
3. Run champion = run médian de la famille (robustesse). Pour logreg, les trois runs ont les mêmes métriques : le choix de seed123 est arbitraire.
4. Évaluation test = une fois par campagne, sur le champion uniquement (2 campagnes : 23/11 et 27/11).

## Résultats sur validation

### LogisticRegression (Pipeline : StandardScaler + OneHotEncoder + LogisticRegression)

| Seed | val_f1 | val_recall | val_roc_auc |
|---|---|---|---|
| 42 | 0.6275 | 0.7701 | 0.8359 |
| 123 | 0.6275 | 0.7701 | 0.8359 |
| 2026 | 0.6275 | 0.7701 | 0.8359 |
| **Médiane** | **0.6275** | **0.7701** | — |
| **IQR** | **0.0000** | — | — |

### RandomForest (Pipeline : StandardScaler + OneHotEncoder + RF n=200, depth=10)

Les valeurs `val_roc_auc` de RF sont omises, faute de sortie vérifiable dans les éléments disponibles.

| Seed | val_f1 | val_recall | val_roc_auc |
|---|---|---|---|
| 42 | 0.6170 | 0.6872 | — |
| 123 | 0.6170 | 0.6872 | — |
| 2026 | 0.6135 | 0.6791 | — |
| **Médiane** | **0.6170** | **0.6872** | — |
| **IQR** | 0.0018 | — | — |

## Sélection du champion

- **Famille retenue : `logreg`** (médiane val_f1 = 0.6275 > 0.6170 pour RF)
- **Run représentatif :** `EXP-J3-churn-logreg-seed123` (`59b0729f960944428dedb24bb1ae7025`)
- **Registre :** `telco-churn` **version 2**, alias `champion`
- **Justification (auto-générée) :**
  > Promu champion J3 : famille 'logreg' sélectionnée sur validation
  > (médiane val_f1=0.6275, IQR=0.0000 sur graines [42, 123, 2026]).
  > Run représentatif : EXP-J3-churn-logreg-seed123
  > (val_f1=0.6275, val_recall=0.7701, val_f1_thr_30=0.5854,
  > val_f1_thr_50=0.6275, val_f1_thr_70=0.5795).
  > Évaluation sur test : test_f1=0.6070, test_recall=0.7888,
  > test_roc_auc=0.8348.

Texte stocké dans le registre ; « unique » s'entend par campagne.

## Évaluation sur le test (une fois par campagne)

| Métrique | Valeur | Écart vs validation |
|---|---|---|
| test_f1 | 0.6070 | -0.0205 (attendu, pas de fuite) |
| test_recall | 0.7888 | +0.0187 |
| test_roc_auc | 0.8348 | -0.0011 |

**Lecture :** le test est inférieur à la validation d'environ 0,02 de F1, ce qui est cohérent avec une sélection faite sur validation et avec l'absence de fuite, sans la démontrer. Le test a été évalué deux fois (une fois par campagne, résultats identiques) ; aucune décision n'en dépend.

## Vérification de portabilité (R10)
```text
[reload] Chargement depuis models:/telco-churn@champion ...
[OK] Rechargement vérifié pour models:/telco-churn@champion (version 2,
famille=logreg) : prédictions identiques sur 20 lignes (max_diff=0.00e+00).
```

Le modèle enregistré contient la **Pipeline complète** (ColumnTransformer + classifier) : il accepte des données brutes (catégorielles non encodées) et reproduit exactement les prédictions. Aucune fuite de prétraitement.

## Points de vigilance observés

### 1. IQR = 0.0000 pour LogisticRegression

Les 3 seeds produisent des `val_f1` **strictement identiques**. Cause probable (hypothèse, non vérifiée) : `LogisticRegression` converge vers le même optimum déterministe sur ce dataset, le résultat n'étant pas sensible au seed d'initialisation.

- **Interprétation :** stabilité reproductible, mais **on ne mesure pas la sensibilité à l'initialisation** pour cette famille.
- **Contraste :** RF montre une variance réelle (IQR=0.0018), cohérent avec son caractère stochastique.

### 2. Version 2 du modèle (au lieu de v1)

La v1 date de la campagne du 23/11 (run 988f9b53…). La campagne a été rejouée le 27/11 (run 59b0729f…) : nouvelle version v2, alias champion déplacé sur la v2 ; la v1 reste dans le registre, sans alias.

### 3. Warning MLflow 3.x `"no artifacts at artifact path 'model'"`

Message observé lors du `register_model` :

```text
WARNING mlflow.tracking._model_registry.fluent: Run with id 59b07...
has no artifacts at artifact path 'model', registering model based on
models:/m-eb78ee4f9ed644a0aedf3823c5ecc49f instead
```

**Explication :** MLflow 3.x utilise un mécanisme `logged_models` distinct des artefacts de run classiques. Le `register_model` référence `models:/m-xxx` au lieu de `runs:/xxx/model`. **Fonctionnel** — preuve : `--verify-reload` passe avec `max_diff=0`.

## Preuves versées

- `j3-mlflow-experiment-churn.png` — état du 23/11 : 6 runs comparatifs dans `p3-churn`
- `j3-mlflow-run-champion.png` — run champion de la campagne initiale
- `j3-mlflow-registry-champion.png` — registre à la date du 23/11 (v1)

## Limites

- Test effectué depuis laptop Windows via tunnel SSH vers le serveur MLflow du cluster (Job K8s de bout en bout à venir pour J4).
- Une seule seed pour le split (train/val/test) — les 3 seeds concernent l'entraînement.
- Dépôt IBM archivé (2024-07-22), accessible à ce jour ; à pérenniser pour J5.
- Reproductibilité vérifiée sur le même poste et le même venv uniquement.
