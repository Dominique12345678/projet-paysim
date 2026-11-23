# 📱 Mobile Money : Entrepôt de Données et Détection de Fraude (PaySim)

[![Python](https://img.shields.io/badge/Python-3.15-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18_Render-336791.svg)](https://render.com/)
[![License](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

Projet académique de **Big Data (Master 1)** portant sur l'ingestion, le nettoyage, la modélisation décisionnelle (DWH en schéma en étoile), la restitution décisionnelle (Power BI) et la détection prédictive de la fraude financière (Machine Learning).

---

## 🎯 Problématique Business
> **« Comment repérer automatiquement les transactions frauduleuses sans bloquer les clients honnêtes ? »**

Dans un contexte de mobile money (très répandu en Afrique de l'Ouest), la confiance des utilisateurs et la pérennité de l'opérateur reposent sur la capacité à neutraliser la fraude financière instantanément, tout en maintenant un taux d'erreur (faux positifs) proche de zéro pour ne pas paralyser l'activité des clients légitimes.

---

## 🏗️ Architecture Globale du Projet

```mermaid
flowchart LR
    subgraph 1. Sourcing
        RAW[Dataset PaySim Kaggle<br/>6,36M transactions / 1,5 Go]
    end

    subgraph 2. Data Engineering
        ETL[Script ETL Python<br/>• Échantillonnage stratifié<br/>• 100% fraudes préservées<br/>• Nettoyage & Typage]
    end

    subgraph 3. Data Warehouse Cloud
        RENDER[(PostgreSQL sur Render<br/>Schéma en Étoile<br/>300k faits / 112 Mo)]
    end

    subgraph 4. Restitution & Analytics
        PBI[Power BI Desktop<br/>• 2 pages de Dashboard<br/>• Mesures DAX métier]
    end

    subgraph 5. Data Science
        ML[Machine Learning<br/>• Baseline Logistic Regression<br/>• Random Forest / XGBoost<br/>• Recall & PR-AUC]
    end

    RAW --> ETL --> RENDER
    RENDER --> PBI
    RENDER --> ML
```

---

## 🗄️ Modélisation DWH : Schéma en Étoile

L'entrepôt de données est normalisé selon les principes de Kimball en schéma en étoile pour optimiser les performances de requêtes analytiques :

```
                        +-------------------------+
                        |   dim_type_operation    |
                        +-------------------------+
                        | type_id (PK)            |
                        | code_type               |
                        | categorie               |
                        | description             |
                        +------------+------------+
                                     | 1
                                     | 
                                     | N
+------------------------------------+------------------------------------+
|                         fact_transactions                               |
+-------------------------------------------------------------------------+
| transaction_id (PK, BIGSERIAL)                                          |
| time_id (FK) -----------> dim_temps.time_id                             |
| type_id (FK) -----------> dim_type_operation.type_id                     |
| orig_account_id (FK) ---> dim_compte_emetteur.orig_account_id           |
| dest_account_id (FK) ---> dim_compte_destinataire.dest_account_id       |
| amount (NUMERIC 15,2)                                                   |
| is_fraud (SMALLINT)                                                     |
| is_flagged_fraud (SMALLINT)                                             |
+-------------------+---------------------------------+-------------------+
                    | N                               | N
                    | 1                               | 1
+-------------------+----+                       +----+--------------------+
|  dim_compte_emetteur   |                       | dim_compte_destinataire |
+------------------------+                       +-------------------------+
| orig_account_id (PK)   |                       | dest_account_id (PK)    |
| account_number (UNIQUE)|                       | account_number (UNIQUE) |
| account_type (C / M)   |                       | account_type (C / M)    |
+------------------------+                       +-------------------------+
```

---

## 📂 Structure du Répertoire

```text
projet-paysim/
├── .env.example              # Gabarit pour les identifiants de base de données
├── .gitignore                # Exclusion stricte des secrets (.env) et gros fichiers
├── requirements.txt          # Dépendances Python du projet
├── README.md                 # Documentation principale
│
├── sql/
│   └── schema_dwh.sql        # Script DDL de création du schéma en étoile & index
│
├── etl/
│   ├── test_connection.py    # Test de connectivité SSL vers Render PostgreSQL
│   ├── init_dwh.py           # Déploiement automatique du schéma DDL
│   ├── populate_dim_temps.py # Alimentation de dim_temps (744 heures / 31 jours)
│   ├── download_data.py      # Téléchargement automatisé PaySim via kagglehub
│   └── etl_pipeline.py       # Pipeline ETL complet (Extract, Sample, Transform, COPY Load)
│
├── notebooks/                # Notebooks d'exploration & Machine Learning
│
└── docs/
    ├── architecture.md       # Schéma et description détaillée de l'architecture
    ├── data_dictionary.md    # Dictionnaire exhaustif des données du DWH
    └── DOCUMENTATION_DATA_ENGINEER.md # Rapport technique du Data Engineer
```

---

## ⚙️ Guide d'Installation et Reproductibilité

Le projet a été conçu pour pouvoir **tout recréer en une seule série de commandes** si la base gratuite Render expire après 30 jours :

### 1. Cloner le projet & créer l'environnement virtuel
```bash
git clone https://github.com/Dominique12345678/projet-paysim.git
cd projet-paysim

python -m venv venv
# Sur Windows :
.\venv\Scripts\activate
# Sur Linux / macOS :
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configurer les variables d'environnement
Copiez `.env.example` en `.env` et renseignez votre URL externe Render :
```env
DATABASE_URL=postgresql://votre_user:votre_password@dpg-xxxxxx.oregon-postgres.render.com/votre_base
```

### 3. Exécuter la chaîne complète en une commande
```powershell
# Vérifier la connexion
python etl/test_connection.py

# Créer les tables DWH
python etl/init_dwh.py

# Générer la dimension temps (744 heures)
python etl/populate_dim_temps.py

# Exécuter l'ETL (échantillonnage, nettoyage, chargement ultra-rapide)
python etl/etl_pipeline.py
```

---

## 📊 Indicateurs Clés du DWH (Render Cloud)

* **Volume de faits** : 299 983 transactions chargées.
* **Fraudes réelles** : 8 197 cas (2,73% de l'échantillon DWH, 100% des fraudes réelles conservées).
* **Comptes émetteurs** : 299 970 comptes uniques.
* **Comptes destinataires** : 248 492 comptes uniques.
* **Espace disque utilisé** : **112 Mo** sur le quota de 1 Go autorisé par Render.

---

## 📈 Guide pour le Tableau de Bord (Power BI)

1. **Connexion** : Power BI Desktop > *Obtenir les données* > *PostgreSQL*. Renseigner l'hôte et la base Render.
2. **Relations** : Valider les relations 1-à-N depuis les dimensions vers `fact_transactions`.
3. **Mesures DAX recommandées** :
   * **Montant Total** : `Montant Total = SUM(fact_transactions[amount])`
   * **Nombre de Fraudes** : `Nombre Fraudes = CALCULATE(COUNTROWS(fact_transactions), fact_transactions[is_fraud] = 1)`
   * **Taux de Fraude (%)** : `Taux de Fraude = DIVIDE([Nombre Fraudes], COUNTROWS(fact_transactions), 0) * 100`
   * **Montant Fraudé** : `Montant Fraude = CALCULATE(SUM(fact_transactions[amount]), fact_transactions[is_fraud] = 1)`

---

## 🤖 Guide pour le Machine Learning

* **Règle absolue du sujet** : Ne **jamais** utiliser les colonnes de solde (`oldbalanceOrg`, `newbalanceOrig`, etc.) car les transactions frauduleuses étant annulées rétroactivement dans PaySim, cela causerait une fuite de données (*data leakage*).
* **Modèles** : Régression Logistique (baseline) $\rightarrow$ Random Forest ou XGBoost.
* **Métriques d'évaluation** : Prioriser le **Rappel (Recall)** pour détecter le maximum de fraudes et l'**AUC-ROC / PR-AUC**. Ne pas utiliser l'Exactitude (Accuracy) en raison du déséquilibre des classes.

---

## 👥 Rôles de l'Équipe
* **Data Engineer** : Architecture technique, scripts ETL, gestion du DWH PostgreSQL sur Render, optimisation du stockage.
* **Data Modeler / Analyst** : Modélisation décisionnelle, élaboration du rapport Power BI, mesures DAX.
* **Data Scientist** : Feature engineering, modélisation supervisée (ML), évaluation des métriques.
* **Chef de Projet** : Cadrage business, coordination de l'équipe, préparation de la soutenance.
* **Qualité & Documentation** : Contrôle de véracité, dictionnaire de données, gouvernance.
