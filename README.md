# Mobile Money : Entrepot de Donnees et Detection de Fraude (PaySim)

[![Python](https://img.shields.io/badge/Python-3.15-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18_Render-336791.svg)](https://render.com/)
[![License](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

Projet academique de **Big Data (Master 1)** portant sur l'ingestion, le nettoyage, la modelisation decisionnelle (DWH en schema en etoile), la restitution decisionnelle (Power BI) et la detection predictive de la fraude financiere (Machine Learning).

---

## Problematique Business
> **« Comment reperer automatiquement les transactions frauduleuses sans bloquer les clients honnetes ? »**

Dans un contexte de mobile money (tres repandu en Afrique de l'Ouest), la confiance des utilisateurs et la perennite de l'operateur reposent sur la capacite a neutraliser la fraude financiere instantanement, tout en maintenant un taux d'erreur (faux positifs) proche de zero pour ne pas paralyser l'activite des clients legitimes.

---

## Architecture Globale du Projet

```mermaid
flowchart LR
    subgraph 1. Sourcing
        RAW[Dataset PaySim Kaggle<br/>6,36M transactions / 1,5 Go]
    end

    subgraph 2. Data Engineering
        ETL[Script ETL Python<br/>• Echantillonnage stratifie<br/>• 100% fraudes preservees<br/>• Nettoyage & Typage]
    end

    subgraph 3. Data Warehouse Cloud
        RENDER[(PostgreSQL sur Render<br/>Schema en Etoile<br/>300k faits / 112 Mo)]
    end

    subgraph 4. Restitution & Analytics
        PBI[Power BI Desktop<br/>• 2 pages de Dashboard<br/>• Mesures DAX metier]
    end

    subgraph 5. Data Science
        ML[Machine Learning<br/>• Baseline Logistic Regression<br/>• Random Forest / XGBoost<br/>• Recall & PR-AUC]
    end

    RAW --> ETL --> RENDER
    RENDER --> PBI
    RENDER --> ML
```

---

## Modelisation DWH : Schema en Etoile

L'entrepot de donnees est normalise selon les principes de Kimball en schema en etoile pour optimiser les performances de requetes analytiques :

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

## Structure du Repertoire

```text
projet-paysim/
├── .env.example              # Gabarit pour les identifiants de base de donnees
├── .gitignore                # Exclusion stricte des secrets (.env) et gros fichiers
├── requirements.txt          # Dependances Python du projet
├── README.md                 # Documentation principale
│
├── sql/
│   └── schema_dwh.sql        # Script DDL de creation du schema en etoile & index
│
├── etl/
│   ├── test_connection.py    # Test de connectivite SSL vers Render PostgreSQL
│   ├── init_dwh.py           # Deploiement automatique du schema DDL
│   ├── populate_dim_temps.py # Alimentation de dim_temps (744 heures / 31 jours)
│   ├── download_data.py      # Telechargement automatise PaySim via kagglehub
│   └── etl_pipeline.py       # Pipeline ETL complet (Extract, Sample, Transform, COPY Load)
│
├── notebooks/                # Notebooks d'exploration & Machine Learning
│
└── docs/
    ├── architecture.md       # Schema et description detaillee de l'architecture
    ├── data_dictionary.md    # Dictionnaire exhaustif des donnees du DWH
    └── DOCUMENTATION_DATA_ENGINEER.md # Rapport technique du Data Engineer
```

---

## Guide d'Installation et Reproductibilite

Le projet a ete concu pour pouvoir **tout recreer en une seule serie de commandes** si la base gratuite Render expire apres 30 jours :

### 1. Cloner le projet & creer l'environnement virtuel
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

### 3. Executer la chaine complete en une commande
```powershell
# Verifier la connexion
python etl/test_connection.py

# Creer les tables DWH
python etl/init_dwh.py

# Generer la dimension temps (744 heures)
python etl/populate_dim_temps.py

# Executer l'ETL (echantillonnage, nettoyage, chargement ultra-rapide)
python etl/etl_pipeline.py
```

---

## Indicateurs Cles du DWH (Render Cloud)

* **Volume de faits** : 299 983 transactions chargees.
* **Fraudes reelles** : 8 197 cas (2,73% de l'echantillon DWH, 100% des fraudes reelles conservees).
* **Comptes emetteurs** : 299 970 comptes uniques.
* **Comptes destinataires** : 248 492 comptes uniques.
* **Espace disque utilise** : **112 Mo** sur le quota de 1 Go autorise par Render.

---

## Guide pour le Tableau de Bord (Power BI)

1. **Connexion** : Power BI Desktop > *Obtenir les donnees* > *PostgreSQL*. Renseigner l'hote et la base Render.
2. **Relations** : Valider les relations 1-a-N depuis les dimensions vers `fact_transactions`.
3. **Mesures DAX recommandees** :
   * **Montant Total** : `Montant Total = SUM(fact_transactions[amount])`
   * **Nombre de Fraudes** : `Nombre Fraudes = CALCULATE(COUNTROWS(fact_transactions), fact_transactions[is_fraud] = 1)`
   * **Taux de Fraude (%)** : `Taux de Fraude = DIVIDE([Nombre Fraudes], COUNTROWS(fact_transactions), 0) * 100`
   * **Montant Fraude** : `Montant Fraude = CALCULATE(SUM(fact_transactions[amount]), fact_transactions[is_fraud] = 1)`

---

## Guide pour le Machine Learning

* **Regle absolue du sujet** : Ne **jamais** utiliser les colonnes de solde (`oldbalanceOrg`, `newbalanceOrig`, etc.) car les transactions frauduleuses etant annulees retroactivement dans PaySim, cela causerait une fuite de donnees (*data leakage*).
* **Modeles** : Regression Logistique (baseline) -> Random Forest ou XGBoost.
* **Metriques d'evaluation** : Prioriser le **Rappel (Recall)** pour detecter le maximum de fraudes et l'**AUC-ROC / PR-AUC**. Ne pas utiliser l'Exactitude (Accuracy) en raison du desequilibre des classes.

---

## Roles de l'Equipe
* **Data Engineer** : Architecture technique, scripts ETL, gestion du DWH PostgreSQL sur Render, optimisation du stockage.
* **Data Modeler / Analyst** : Modelisation decisionnelle, elaboration du rapport Power BI, mesures DAX.
* **Data Scientist** : Feature engineering, modelisation supervisee (ML), evaluation des metriques.
* **Chef de Projet** : Cadrage business, coordination de l'equipe, preparation de la soutenance.
* **Qualite & Documentation** : Controle de veracite, dictionnaire de donnees, gouvernance.
