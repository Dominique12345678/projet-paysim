# ```python
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# 1. Connexion à PostgreSQL
load_dotenv()
database_url = os.getenv("DATABASE_URL")

if not database_url:
    print("DATABASE_URL introuvable dans .env")
    sys.exit(1)

if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://", "postgresql+psycopg2://", 1
    )
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace(
        "postgresql://", "postgresql+psycopg2://", 1
    )

engine = create_engine(
    database_url,
    connect_args={"sslmode": "require"}
)

try:
    with engine.connect() as conn:

        # 2. Volume général
        print("\n===== 1. VOLUME DES DONNEES =====")

        total = conn.execute(text("""
            SELECT COUNT(*) FROM fact_transactions;
        """)).scalar()

        print(f"Nombre de transactions : {total:,}")

        # 3. Valeurs manquantes
        print("\n===== 2. VALEURS MANQUANTES =====")

        missing = conn.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE amount IS NULL) AS amount_null,
                COUNT(*) FILTER (WHERE time_id IS NULL) AS time_null,
                COUNT(*) FILTER (WHERE type_id IS NULL) AS type_null,
                COUNT(*) FILTER (WHERE orig_account_id IS NULL) AS orig_null,
                COUNT(*) FILTER (WHERE dest_account_id IS NULL) AS dest_null,
                COUNT(*) FILTER (WHERE is_fraud IS NULL) AS fraud_null
            FROM fact_transactions;
        """)).fetchone()

        for name, value in zip(
            ["amount", "time_id", "type_id", "orig_account_id",
             "dest_account_id", "is_fraud"],
            missing
        ):
            print(f"{name} : {value}")

        # 4. Doublons
        print("\n===== 3. DOUBLONS =====")

        duplicates = conn.execute(text("""
            SELECT
                COUNT(*) - COUNT(DISTINCT transaction_id)
            FROM fact_transactions;
        """)).scalar()

        print(f"Identifiants de transactions en doublon : {duplicates}")

        # 5. Montants
        print("\n===== 4. ANALYSE DES MONTANTS =====")

        amounts = conn.execute(text("""
            SELECT
                MIN(amount),
                MAX(amount),
                AVG(amount),
                COUNT(*) FILTER (WHERE amount <= 0)
            FROM fact_transactions;
        """)).fetchone()

        print(f"Montant minimum : {amounts[0]}")
        print(f"Montant maximum : {amounts[1]}")
        print(f"Montant moyen : {amounts[2]:.2f}")
        print(f"Montants nuls ou négatifs : {amounts[3]}")

        # 6. Vérification des relations entre les tables
        print("\n===== 5. INTEGRITE DES RELATIONS =====")

        relations = conn.execute(text("""
            SELECT
                COUNT(*) FILTER (
                    WHERE t.time_id IS NULL
                ) AS temps_absent,

                COUNT(*) FILTER (
                    WHERE ty.type_id IS NULL
                ) AS type_absent,

                COUNT(*) FILTER (
                    WHERE ce.orig_account_id IS NULL
                ) AS emetteur_absent,

                COUNT(*) FILTER (
                    WHERE cd.dest_account_id IS NULL
                ) AS destinataire_absent

            FROM fact_transactions f

            LEFT JOIN dim_temps t
                ON f.time_id = t.time_id

            LEFT JOIN dim_type_operation ty
                ON f.type_id = ty.type_id

            LEFT JOIN dim_compte_emetteur ce
                ON f.orig_account_id = ce.orig_account_id

            LEFT JOIN dim_compte_destinataire cd
                ON f.dest_account_id = cd.dest_account_id;
        """)).fetchone()

        for name, value in zip(
            ["Temps absent", "Type absent",
             "Emetteur absent", "Destinataire absent"],
            relations
        ):
            print(f"{name} : {value}")

        # 7. Répartition des fraudes par type
        print("\n===== 6. FRAUDES PAR TYPE D'OPERATION =====")

        fraud_by_type = conn.execute(text("""
            SELECT
                ty.code_type,
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE f.is_fraud = 1) AS fraudes,
                ROUND(
                    100.0 * COUNT(*) FILTER (WHERE f.is_fraud = 1)
                    / NULLIF(COUNT(*), 0), 2
                ) AS taux_fraude
            FROM fact_transactions f
            LEFT JOIN dim_type_operation ty
                ON f.type_id = ty.type_id
            GROUP BY ty.code_type
            ORDER BY taux_fraude DESC;
        """)).fetchall()

        for row in fraud_by_type:
            print(
                f"{row[0]} : {row[1]:,} transactions | "
                f"{row[2]:,} fraudes | {row[3]} %"
            )

        # 8. Répartition temporelle
        print("\n===== 7. DISTRIBUTION TEMPORELLE =====")

        time_stats = conn.execute(text("""
            SELECT
                MIN(time_id),
                MAX(time_id),
                COUNT(DISTINCT time_id)
            FROM fact_transactions;
        """)).fetchone()

        print(f"Step minimum : {time_stats[0]}")
        print(f"Step maximum : {time_stats[1]}")
        print(f"Nombre de steps distincts : {time_stats[2]}")

        print("\n===== INSPECTION TERMINEE =====")

finally:
    engine.dispose()