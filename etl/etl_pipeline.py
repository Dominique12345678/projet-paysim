"""
Pipeline ETL PaySim -> PostgreSQL Render (DWH Schéma en Étoile).
- Échantillonnage stratifié intelligent (100% des fraudes conservées pour respecter la limite Render de 1 Go).
- Nettoyage et validation de qualité.
- Alimentation des dimensions et de la table de faits.
"""

import os
import sys
import io
import time
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# 1. Configuration
load_dotenv()
database_url = os.getenv("DATABASE_URL")
if not database_url:
    print("❌ DATABASE_URL introuvable dans .env")
    sys.exit(1)

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)

csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "paysim.csv")
if not os.path.exists(csv_path):
    print(f"❌ Fichier dataset introuvable : {csv_path}")
    sys.exit(1)

TOTAL_SAMPLE_TARGET = 300_000  # Taille d'échantillon idéale pour Render (respect de la limite de 1 Go)

print("="*70)
print("🚀 DÉMARRAGE DU PIPELINE ETL PAYSIM -> POSTGRESQL RENDER")
print("="*70)

# 2. Extraction & Échantillonnage
start_time = time.time()
print(f"📖 Lecture et échantillonnage depuis {csv_path}...")

# Lire les colonnes utiles
cols = ['step', 'type', 'amount', 'nameOrig', 'nameDest', 'isFraud', 'isFlaggedFraud']
df_raw = pd.read_csv(csv_path, usecols=cols)
total_raw = len(df_raw)
print(f"Total brut dans PaySim : {total_raw:,} lignes.")

# Séparer fraudes et non-fraudes
df_frauds = df_raw[df_raw['isFraud'] == 1].copy()
df_legit = df_raw[df_raw['isFraud'] == 0].copy()

nb_frauds = len(df_frauds)
nb_legit_needed = TOTAL_SAMPLE_TARGET - nb_frauds

print(f"📌 Fraudes identifiées : {nb_frauds:,} (conservées à 100%)")
print(f"📌 Tirage aléatoire stratifié des transactions légitimes : {nb_legit_needed:,} lignes...")

# Échantillonnage stratifié par type de transaction
df_legit_sample = df_legit.groupby('type', group_keys=False).apply(
    lambda x: x.sample(n=int(np.rint(len(x) / len(df_legit) * nb_legit_needed)), random_state=42)
)

# Concaténer et mélanger
df_sample = pd.concat([df_frauds, df_legit_sample], ignore_index=True)
df_sample = df_sample.sample(frac=1.0, random_state=42).reset_index(drop=True)

print(f"✅ Échantillon final prêt : {len(df_sample):,} lignes.")
print(f"   Taux de fraude dans l'échantillon : {(len(df_frauds) / len(df_sample)) * 100:.2f}%")

# Nettoyage
# Vérifier montants négatifs ou nuls
df_sample = df_sample[df_sample['amount'] > 0]
# Remplir valeurs nulles si présentes
df_sample['isFlaggedFraud'] = df_sample['isFlaggedFraud'].fillna(0).astype(int)
df_sample['isFraud'] = df_sample['isFraud'].astype(int)

# 3. Connexion à la base
engine = create_engine(database_url, connect_args={"sslmode": "require"})

print("\n🔄 Chargement des dimensions dans PostgreSQL...")

# 4. Charger la dimension Type d'opération (récupérer le mapping)
with engine.connect() as conn:
    types_db = conn.execute(text("SELECT type_id, code_type FROM dim_type_operation;")).fetchall()
    type_map = {row[1]: row[0] for row in types_db}
print(f"Mapping des types d'opérations : {type_map}")

# 5. Dimension Comptes Émetteurs (dim_compte_emetteur)
print("📥 Traitement des comptes émetteurs (nameOrig)...")
orig_accounts = df_sample[['nameOrig']].drop_duplicates().copy()
orig_accounts.rename(columns={'nameOrig': 'account_number'}, inplace=True)
orig_accounts['account_type'] = orig_accounts['account_number'].apply(
    lambda x: 'Commerçant' if str(x).startswith('M') else 'Client'
)

# Vider les comptes et les faits pour un rechargement propre
with engine.begin() as conn:
    print("Nettoyage des tables fact et comptes...")
    conn.execute(text("TRUNCATE TABLE fact_transactions, dim_compte_emetteur, dim_compte_destinataire CASCADE;"))

# Insérer comptes émetteurs en bloc
print(f"Insertion de {len(orig_accounts):,} comptes émetteurs uniques...")
orig_accounts.to_sql("dim_compte_emetteur", engine, if_exists="append", index=False, chunksize=10000)

# Récupérer l'ID des comptes émetteurs
with engine.connect() as conn:
    orig_db = conn.execute(text("SELECT orig_account_id, account_number FROM dim_compte_emetteur;")).fetchall()
    orig_map = {row[1]: row[0] for row in orig_db}

# 6. Dimension Comptes Destinataires (dim_compte_destinataire)
print("📥 Traitement des comptes destinataires (nameDest)...")
dest_accounts = df_sample[['nameDest']].drop_duplicates().copy()
dest_accounts.rename(columns={'nameDest': 'account_number'}, inplace=True)
dest_accounts['account_type'] = dest_accounts['account_number'].apply(
    lambda x: 'Commerçant' if str(x).startswith('M') else 'Client'
)

print(f"Insertion de {len(dest_accounts):,} comptes destinataires uniques...")
dest_accounts.to_sql("dim_compte_destinataire", engine, if_exists="append", index=False, chunksize=10000)

with engine.connect() as conn:
    dest_db = conn.execute(text("SELECT dest_account_id, account_number FROM dim_compte_destinataire;")).fetchall()
    dest_map = {row[1]: row[0] for row in dest_db}

# 7. Préparation de la table de faits
print("\n📊 Préparation de fact_transactions...")
df_sample['time_id'] = df_sample['step']
df_sample['type_id'] = df_sample['type'].map(type_map)
df_sample['orig_account_id'] = df_sample['nameOrig'].map(orig_map)
df_sample['dest_account_id'] = df_sample['nameDest'].map(dest_map)

fact_df = df_sample[[
    'time_id',
    'type_id',
    'orig_account_id',
    'dest_account_id',
    'amount',
    'is_fraud',
    'is_flagged_fraud'
]].copy()

# Renommer colonnes pour matcher la table SQL
fact_df.rename(columns={
    'isFraud': 'is_fraud',
    'isFlaggedFraud': 'is_flagged_fraud'
}, inplace=True)

# 8. Insertion dans fact_transactions
print(f"🚀 Insertion de {len(fact_df):,} transactions dans fact_transactions (par lots de 10 000)...")
fact_df.to_sql("fact_transactions", engine, if_exists="append", index=False, chunksize=10000)

elapsed = time.time() - start_time
print("\n" + "="*70)
print(f"🎉 PIPELINE ETL TERMINÉ AVEC SUCCÈS EN {elapsed:.1f} SECONDES !")
print("="*70)

# 9. Statistiques de contrôle
with engine.connect() as conn:
    c_facts = conn.execute(text("SELECT COUNT(*) FROM fact_transactions;")).scalar()
    c_frauds = conn.execute(text("SELECT COUNT(*) FROM fact_transactions WHERE is_fraud = 1;")).scalar()
    c_orig = conn.execute(text("SELECT COUNT(*) FROM dim_compte_emetteur;")).scalar()
    c_dest = conn.execute(text("SELECT COUNT(*) FROM dim_compte_destinataire;")).scalar()
    
    print(f"📊 Contrôle DWH PostgreSQL Render :")
    print(f"   • fact_transactions       : {c_facts:,} lignes")
    print(f"   • Transactions frauduleuses : {c_frauds:,} ({c_frauds/c_facts*100:.2f}%)")
    print(f"   • dim_compte_emetteur     : {c_orig:,} comptes")
    print(f"   • dim_compte_destinataire : {c_dest:,} comptes")
print("="*70)
