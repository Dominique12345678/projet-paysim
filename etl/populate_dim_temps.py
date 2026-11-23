"""
Script de génération et d'insertion de la dimension Temps (dim_temps) dans PostgreSQL.
PaySim simule 744 heures (31 jours x 24 heures).
"""

import os
import sys
import pandas as pd
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

print("🔄 Génération des 744 enregistrements de dim_temps...")

records = []
for step in range(1, 745):
    # Calcul jour (1 à 31) et heure (0 à 23)
    jour = ((step - 1) // 24) + 1
    heure = (step - 1) % 24
    
    # Tranche horaire
    if 0 <= heure < 6:
        tranche = "Nuit"
    elif 6 <= heure < 12:
        tranche = "Matin"
    elif 12 <= heure < 18:
        tranche = "Après-midi"
    else:
        tranche = "Soir"
        
    # Type de jour (on simule un mois débutant un lundi : jours 6, 7, 13, 14, 20, 21, 27, 28 = Week-end)
    jour_semaine = (jour - 1) % 7
    type_jour = "Week-end" if jour_semaine in [5, 6] else "Semaine"
    
    records.append({
        "time_id": step,
        "step": step,
        "jour": jour,
        "heure": heure,
        "tranche_horaire": tranche,
        "type_jour": type_jour
    })

df_temps = pd.DataFrame(records)

try:
    engine = create_engine(database_url, connect_args={"sslmode": "require"})
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE dim_temps CASCADE;"))
    df_temps.to_sql("dim_temps", engine, if_exists="append", index=False)
    print("✅ dim_temps alimentée avec succès (744 heures insérées) !")
except Exception as e:
    print("❌ Erreur lors de l'insertion dans dim_temps :", str(e))
    sys.exit(1)
