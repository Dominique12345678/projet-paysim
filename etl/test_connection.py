"""
Script de test de connexion à la base de données PostgreSQL Render.
Vérifie que le fichier .env est bien configuré et que la base répond.
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Charger les variables depuis le fichier .env
load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    # Alternative : reconstruire depuis les variables individuelles
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    if host and name and user and password:
        database_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
    else:
        print("\n❌ ERREUR : Aucune variable DATABASE_URL trouvée dans le fichier .env.")
        print("Veuillez copier le fichier .env.example vers .env et renseigner vos identifiants Render.")
        sys.exit(1)

# Corriger si Render fournit l'URL au format 'postgres://' au lieu de 'postgresql://' pour SQLAlchemy
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

print(f"🔄 Tentative de connexion au serveur PostgreSQL Render...")

try:
    # sslmode=require est obligatoire pour Render
    engine = create_engine(database_url, connect_args={"sslmode": "require"})
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();")).fetchone()
        current_db = conn.execute(text("SELECT current_database();")).fetchone()
        print("\n" + "="*60)
        print("✅ CONNEXION RÉUSSIE À RENDER POSTGRESQL !")
        print("="*60)
        print(f"📌 Base active : {current_db[0]}")
        print(f"📌 Version PostgreSQL : {result[0]}")
        print("="*60)
except Exception as e:
    print("\n" + "="*60)
    print("❌ ÉCHEC DE LA CONNEXION :")
    print("="*60)
    print(str(e))
    print("\n👉 Vérifiez que :")
    print(" 1. Votre base sur Render n'est pas suspendue / en veille.")
    print(" 2. Vous utilisez bien l' 'External Database URL' fournie par Render.")
    print(" 3. Vos identifiants (user, password, host, db) sont corrects dans .env.")
    sys.exit(1)
