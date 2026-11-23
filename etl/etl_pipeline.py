"""
Pipeline ETL PaySim -> PostgreSQL Render (DWH Schéma en Étoile).
- Échantillonnage stratifié intelligent (100% des fraudes conservées pour respecter la limite Render de 1 Go).
- Nettoyage et validation de qualité.
- Chargement ultra-rapide par PostgreSQL COPY (quelques secondes).
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

TOTAL_SAMPLE_TARGET = 300_000  # Respect strict du quota de 1 Go Render

print("="*70)
print("🚀 DÉMARRAGE DU PIPELINE ETL PAYSIM -> POSTGRESQL RENDER")
print("="*70)

# Fonction ultra-rapide pour insérer dans PostgreSQL via COPY
def fast_bulk_insert(df, table_name, engine, columns):
    buffer = io.StringIO()
    # Exporter en format CSV tsv dans un buffer mémoire
    df[columns].to_csv(buffer, index=False, header=False, sep='\t', na_rep='\\N')
    buffer.seek(0)
    
    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cur:
            col_list = ', '.join([f'"{c}"' for c in columns])
            sql = f"COPY {table_name} ({col_list}) FROM STDIN WITH (FORMAT csv, DELIMITER E'\\t', NULL '\\N')"
            cur.copy_expert(sql, buffer)
        raw_conn.commit()
    finally:
        raw_conn.close()

# 2. Extraction & Échantillonnage
start_time = time.time()
print(f"📖 Lecture depuis {csv_path}...")

cols = ['step', 'type', 'amount', 'nameOrig', 'nameDest', 'isFraud', 'isFlaggedFraud']
df_raw = pd.read_csv(csv_path, usecols=cols)
total_raw = len(df_raw)
print(f"Total brut dans PaySim : {total_raw:,} lignes.")

# Séparer fraudes et non-fraudes
df_frauds = df_raw[df_raw['isFraud'] == 1].copy()
df_legit = df_raw[df_raw['isFraud'] == 0].copy()

nb_frauds = len(df_frauds)
nb_legit_needed = TOTAL_SAMPLE_TARGET - nb_frauds

print(f"📌 Fraudes détectées : {nb_frauds:,} (100% conservées)")
print(f"📌 Tirage aléatoire stratifié des transactions légitimes : {nb_legit_needed:,} lignes...")

# Échantillonnage stratifié natif sans perte de colonnes
legit_frac = nb_legit_needed / len(df_legit)
df_legit_sample = df_legit.groupby('type', group_keys=False).sample(frac=legit_frac, random_state=42)

# Combiner et mélanger
df_sample = pd.concat([df_frauds, df_legit_sample], ignore_index=True)
df_sample = df_sample.sample(frac=1.0, random_state=42).reset_index(drop=True)

# Nettoyage
df_sample = df_sample[df_sample['amount'] > 0]
df_sample['isFlaggedFraud'] = df_sample['isFlaggedFraud'].fillna(0).astype(int)
df_sample['isFraud'] = df_sample['isFraud'].astype(int)

# Renommer les colonnes cibles
df_sample = df_sample.rename(columns={
    'isFraud': 'is_fraud',
    'isFlaggedFraud': 'is_flagged_fraud'
})

print(f"✅ Échantillon prêt : {len(df_sample):,} transactions.")
print(f"   Taux de fraude dans l'échantillon : {(len(df_frauds) / len(df_sample)) * 100:.2f}%")

# 3. Connexion à Render
engine = create_engine(database_url, connect_args={"sslmode": "require"})

# Récupérer la dimension types d'opérations
with engine.connect() as conn:
    types_db = conn.execute(text("SELECT type_id, code_type FROM dim_type_operation;")).fetchall()
    type_map = {row[1]: row[0] for row in types_db}
print(f"Mapping types : {type_map}")

# Vider les tables pour un chargement propre
print("\n🧹 Nettoyage des anciennes données (TRUNCATE)...")
with engine.begin() as conn:
    conn.execute(text("TRUNCATE TABLE fact_transactions, dim_compte_emetteur, dim_compte_destinataire CASCADE;"))

# 4. Dimension Comptes Émetteurs (dim_compte_emetteur)
print("📥 Traitement et insertion des comptes émetteurs (nameOrig)...")
orig_accounts = df_sample[['nameOrig']].drop_duplicates().copy()
orig_accounts = orig_accounts.rename(columns={'nameOrig': 'account_number'})
orig_accounts['account_type'] = orig_accounts['account_number'].apply(
    lambda x: 'Commerçant' if str(x).startswith('M') else 'Client'
)

fast_bulk_insert(orig_accounts, "dim_compte_emetteur", engine, ['account_number', 'account_type'])
print(f"✅ {len(orig_accounts):,} comptes émetteurs insérés avec succès.")

# Récupérer le mapping des IDs de comptes émetteurs
with engine.connect() as conn:
    orig_db = conn.execute(text("SELECT orig_account_id, account_number FROM dim_compte_emetteur;")).fetchall()
    orig_map = {row[1]: row[0] for row in orig_db}

# 5. Dimension Comptes Destinataires (dim_compte_destinataire)
print("📥 Traitement et insertion des comptes destinataires (nameDest)...")
dest_accounts = df_sample[['nameDest']].drop_duplicates().copy()
dest_accounts = dest_accounts.rename(columns={'nameDest': 'account_number'})
dest_accounts['account_type'] = dest_accounts['account_number'].apply(
    lambda x: 'Commerçant' if str(x).startswith('M') else 'Client'
)

fast_bulk_insert(dest_accounts, "dim_compte_destinataire", engine, ['account_number', 'account_type'])
print(f"✅ {len(dest_accounts):,} comptes destinataires insérés avec succès.")

with engine.connect() as conn:
    dest_db = conn.execute(text("SELECT dest_account_id, account_number FROM dim_compte_destinataire;")).fetchall()
    dest_map = {row[1]: row[0] for row in dest_db}

# 6. Préparation de fact_transactions
print("\n📊 Préparation des clés étrangères pour fact_transactions...")
df_sample['time_id'] = df_sample['step']
df_sample['type_id'] = df_sample['type'].map(type_map)
df_sample['orig_account_id'] = df_sample['nameOrig'].map(orig_map)
df_sample['dest_account_id'] = df_sample['nameDest'].map(dest_map)

# Vérification d'intégrité avant insertion
assert df_sample['type_id'].isna().sum() == 0, "Erreur : type_id contient des valeurs nulles !"
assert df_sample['orig_account_id'].isna().sum() == 0, "Erreur : orig_account_id contient des valeurs nulles !"
assert df_sample['dest_account_id'].isna().sum() == 0, "Erreur : dest_account_id contient des valeurs nulles !"

fact_cols = [
    'time_id',
    'type_id',
    'orig_account_id',
    'dest_account_id',
    'amount',
    'is_fraud',
    'is_flagged_fraud'
]

print(f"🚀 Insertion ultra-rapide de {len(df_sample):,} transactions dans fact_transactions...")
fast_bulk_insert(df_sample, "fact_transactions", engine, fact_cols)

elapsed = time.time() - start_time
print("\n" + "="*70)
print(f"🎉 PIPELINE ETL TERMINÉ AVEC SUCCÈS EN {elapsed:.1f} SECONDES !")
print("="*70)

# 7. Contrôle de qualité final
with engine.connect() as conn:
    c_facts = conn.execute(text("SELECT COUNT(*) FROM fact_transactions;")).scalar()
    c_frauds = conn.execute(text("SELECT COUNT(*) FROM fact_transactions WHERE is_fraud = 1;")).scalar()
    c_orig = conn.execute(text("SELECT COUNT(*) FROM dim_compte_emetteur;")).scalar()
    c_dest = conn.execute(text("SELECT COUNT(*) FROM dim_compte_destinataire;")).scalar()
    
    print(f"📊 Contrôle de l'entrepôt de données (DWH) sur Render :")
    print(f"   • fact_transactions         : {c_facts:,} transactions")
    print(f"   • Fraudes confirmées        : {c_frauds:,} ({c_frauds/c_facts*100:.2f}%)")
    print(f"   • dim_compte_emetteur       : {c_orig:,} comptes uniques")
    print(f"   • dim_compte_destinataire   : {c_dest:,} comptes uniques")
    print(f"   • dim_type_operation        : {len(type_map)} types d'opérations")
    print(f"   • dim_temps                 : 744 heures (31 jours)")
print("="*70)
