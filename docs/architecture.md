# 🗺️ Schéma d'Architecture - Pipeline PaySim

Ce document décrit l'architecture complète du pipeline de données, de la source brute jusqu'aux usages décisionnels et prédictifs.

---

## 1. Diagramme d'Architecture Détaillé

```mermaid
flowchart TD
    subgraph SOURCING["1. SOURCING & INGESTION"]
        SRC["PaySim Kaggle Dataset<br/>(6 362 620 transactions / 1,5 Go CSV)"]
        KH["Ingestion automatisée : kagglehub"]
        SRC --> KH
    end

    subgraph ETL["2. PIPELINE ETL (Python)"]
        direction TB
        E["Extract : Sélection colonnes métier"]
        T_SAMPLE["Transform : Stratified Sampling<br/>(100% fraudes = 8 197 + 291k légitimes)"]
        T_CLEAN["Data Quality : amount > 0, cast nulls"]
        T_DIM["Feature Engineering Temporel & Typage Comptes"]
        L_COPY["Load : PostgreSQL COPY FROM STDIN (ultra-rapide)"]
        
        E --> T_SAMPLE --> T_CLEAN --> T_DIM --> L_COPY
    end

    subgraph DWH["3. ENTREPÔT DE DONNÉES (PostgreSQL sur Render Cloud)"]
        direction TB
        D_TYPE["dim_type_operation<br/>(5 types d'opérations)"]
        D_TIME["dim_temps<br/>(744 heures - 31 jours)"]
        D_ORIG["dim_compte_emetteur<br/>(299 970 comptes)"]
        D_DEST["dim_compte_destinataire<br/>(248 492 comptes)"]
        F_TRANS["fact_transactions<br/>(299 983 transactions indexées)"]
        
        D_TYPE --- F_TRANS
        D_TIME --- F_TRANS
        D_ORIG --- F_TRANS
        D_DEST --- F_TRANS
    end

    subgraph ANALYTICS["4. RESTITUTION DÉCISIONNELLE (Power BI)"]
        PBI_P1["Page 1 : Vue Globale & Analyse d'Activité"]
        PBI_P2["Page 2 : Détection & Analyse des Fraudes"]
        DAX["Mesures DAX : Taux de Fraude, Montant Total, Volumes"]
    end

    subgraph ML["5. ANALYSE PRÉDICTIVE (Machine Learning)"]
        PREP["Préparation & Encodage (Sans fuite de soldes)"]
        MODELS["Classification : Logistic Regression & Random Forest"]
        METRICS["Évaluation : Recall, PR-AUC, ROC-AUC"]
    end

    KH --> E
    L_COPY --> DWH
    DWH --> ANALYTICS
    DWH --> ML
```

---

## 2. Choix Technologiques & Justifications

| Composant | Technologie | Justification |
| :--- | :--- | :--- |
| **Langage de Pipeline** | Python 3.15 + pandas + SQLAlchemy | Standard de l'industrie, flexibilité de traitement et intégration native avec PostgreSQL. |
| **Chargement Données** | PostgreSQL `COPY` (psycopg2) | Permet d'insérer 300 000 lignes en moins de 4 minutes, évitant les timeouts HTTP/SSL de Render. |
| **Entrepôt de Données** | PostgreSQL 18 sur Render Cloud | Solution managée cloud gratuite, accessible à distance pour tous les membres de l'équipe et Power BI. |
| **Modélisation** | Schéma en étoile (Kimball) | Réduction drastique des jointures complexes, optimisation des filtres et navigation intuitive dans Power BI. |
| **Outil de Restitution** | Power BI Desktop | Connexion native PostgreSQL, moteur DAX puissant et visualisations interactives professionnelles. |
| **Machine Learning** | scikit-learn / XGBoost | Algorithmes supervisés robustes adaptés aux données tabulaires avec fort déséquilibre de classe. |

---

## 3. Gestion des Contraintes Techniques

1. **Quota de Stockage Render (1 Go)** :
   * *Problème* : Le dataset complet de 6,36 millions de lignes dépasse 1,5 Go sans les index.
   * *Solution* : Échantillonnage stratifié intelligent de 300 000 lignes conservant **100% des fraudes**. Espace final consommé : **112 Mo** seulement.
2. **Durée de vie de l'instance gratuite (30 jours)** :
   * *Problème* : Render supprime les bases gratuites après 30 jours.
   * *Solution* : Automatisation intégrale du DDL et de l'ETL via des scripts Python reproductibles en une commande.
