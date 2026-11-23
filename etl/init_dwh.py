"""
Script d'initialisation du schéma en étoile sur PostgreSQL Render.
Exécute le fichier sql/schema_dwh.sql.
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

database_url = os.getenv("DATABASE_URL")
if not database_url:
    print("❌ DATABASE_URL introuvable dans .env")
    sys.exit(1)

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)

sql_file_path = os.path.join(os.path.dirname(__file__), "..", "sql", "schema_dwh.sql")

if not os.path.exists(sql_file_path):
    print(f"❌ Fichier SQL introuvable : {sql_file_path}")
    sys.exit(1)

with open(sql_file_path, "r", encoding="utf-8") as f:
    sql_script = f.read()

print("🔄 Application du schéma en étoile sur Render PostgreSQL...")

try:
    engine = create_engine(database_url, connect_args={"sslmode": "require"})
    with engine.begin() as conn:
        # Exécuter les commandes séparées par point-virgule
        for statement in sql_script.split(";"):
            statement = statement.strip()
            if statement:
                conn.execute(text(statement))
    print("\n" + "="*60)
    print("✅ SCHÉMA EN ÉTOILE CRÉÉ AVEC SUCCÈS SUR RENDER !")
    print("="*60)
    print("Tables créées :")
    print(" - dim_type_operation")
    print(" - dim_temps")
    print(" - dim_compte_emetteur")
    print(" - dim_compte_destinataire")
    print(" - fact_transactions")
    print("="*60)
except Exception as e:
    print("❌ Erreur lors de l'application du schéma :", str(e))
    sys.exit(1)
