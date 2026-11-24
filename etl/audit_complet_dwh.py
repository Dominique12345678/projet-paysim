"""
AUDIT COMPLET DU DATA WAREHOUSE PAYSIM

Objectifs :
- Vérifier la structure du DWH.
- Contrôler la qualité des données.
- Vérifier les relations entre les dimensions et la table de faits.
- Analyser la distribution des transactions et des fraudes.
- Examiner la dimension temporelle.
- Contrôler les variables utilisées pour le Machine Learning.
- Générer un rapport Markdown.

Ce script est en lecture seule : il ne modifie aucune table.
"""

import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# ============================================================
# 1. CONFIGURATION
# ============================================================

load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    print("ERREUR : DATABASE_URL introuvable dans le fichier .env")
    sys.exit(1)

if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://",
        "postgresql+psycopg2://",
        1
    )

elif database_url.startswith("postgresql://"):
    database_url = database_url.replace(
        "postgresql://",
        "postgresql+psycopg2://",
        1
    )

engine = create_engine(
    database_url,
    connect_args={"sslmode": "require"}
)

# Dossier de génération du rapport
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REPORT_DIR = os.path.join(ROOT_DIR, "docs")

os.makedirs(REPORT_DIR, exist_ok=True)

REPORT_PATH = os.path.join(
    REPORT_DIR,
    "rapport_audit_dwh.md"
)

report = []

anomalies = []
observations = []


def add_report(text_content=""):
    """Ajoute du contenu au rapport et au terminal."""
    report.append(str(text_content))
    print(text_content)


def record_check(name, result, details=""):
    """Enregistre le résultat d'un contrôle."""
    status = "OK" if result else "ANOMALIE"

    add_report(f"- **{name} : {status}** {details}")

    if not result:
        anomalies.append(name)


# ============================================================
# 2. DEMARRAGE
# ============================================================

add_report("# RAPPORT D'AUDIT DU DATA WAREHOUSE PAYSIM")

add_report(
    f"\nDate de l'audit : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
)

add_report("\n---\n")

try:

    with engine.connect() as conn:

        # ====================================================
        # 3. CONNEXION
        # ====================================================

        add_report("\n## 1. CONNEXION A POSTGRESQL")

        version = conn.execute(
            text("SELECT version();")
        ).scalar()

        add_report("Connexion PostgreSQL réussie.")

        add_report(f"Version : {version}")

        # ====================================================
        # 4. STRUCTURE DU DWH
        # ====================================================

        add_report("\n## 2. STRUCTURE DU DATA WAREHOUSE")

        expected_tables = {
            "fact_transactions",
            "dim_temps",
            "dim_type_operation",
            "dim_compte_emetteur",
            "dim_compte_destinataire"
        }

        tables = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE';
        """)).scalars().all()

        existing_tables = set(tables)

        for table in sorted(expected_tables):

            record_check(
                f"Table {table}",
                table in existing_tables
            )

        missing_tables = expected_tables - existing_tables

        if missing_tables:
            raise RuntimeError(
                f"Tables indispensables absentes : {missing_tables}"
            )

        # Vérification des colonnes
        expected_columns = {
            "fact_transactions": {
                "transaction_id",
                "time_id",
                "type_id",
                "orig_account_id",
                "dest_account_id",
                "amount",
                "is_fraud",
                "is_flagged_fraud"
            },
            "dim_temps": {
                "time_id",
                "step",
                "jour",
                "heure",
                "tranche_horaire",
                "type_jour"
            },
            "dim_type_operation": {
                "type_id",
                "code_type",
                "categorie",
                "description"
            },
            "dim_compte_emetteur": {
                "orig_account_id",
                "account_number",
                "account_type"
            },
            "dim_compte_destinataire": {
                "dest_account_id",
                "account_number",
                "account_type"
            }
        }

        add_report("\n### Vérification des colonnes")

        for table, expected in expected_columns.items():

            columns = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = :table;
            """), {"table": table}).scalars().all()

            missing = expected - set(columns)

            record_check(
                f"Colonnes de {table}",
                len(missing) == 0,
                f"Colonnes manquantes : {missing if missing else 'Aucune'}"
            )

        # ====================================================
        # 5. VOLUME
        # ====================================================

        add_report("\n## 3. VOLUME DES DONNEES")

        total = conn.execute(text("""
            SELECT COUNT(*)
            FROM fact_transactions;
        """)).scalar()

        add_report(f"Nombre de transactions : {total:,}")

        record_check(
            "Volume des transactions",
            total > 0,
            f"{total:,} lignes présentes."
        )

        # ====================================================
        # 6. VALEURS MANQUANTES
        # ====================================================

        add_report("\n## 4. VALEURS MANQUANTES")

        missing = conn.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE amount IS NULL),
                COUNT(*) FILTER (WHERE time_id IS NULL),
                COUNT(*) FILTER (WHERE type_id IS NULL),
                COUNT(*) FILTER (WHERE orig_account_id IS NULL),
                COUNT(*) FILTER (WHERE dest_account_id IS NULL),
                COUNT(*) FILTER (WHERE is_fraud IS NULL),
                COUNT(*) FILTER (WHERE is_flagged_fraud IS NULL)
            FROM fact_transactions;
        """)).fetchone()

        missing_columns = [
            "amount",
            "time_id",
            "type_id",
            "orig_account_id",
            "dest_account_id",
            "is_fraud",
            "is_flagged_fraud"
        ]

        for name, value in zip(missing_columns, missing):

            record_check(
                f"Valeurs manquantes - {name}",
                value == 0,
                f"{value} valeur(s) manquante(s)."
            )

        # ====================================================
        # 7. DOUBLONS
        # ====================================================

        add_report("\n## 5. DOUBLONS")

        duplicates = conn.execute(text("""
            SELECT COUNT(*) - COUNT(DISTINCT transaction_id)
            FROM fact_transactions;
        """)).scalar()

        record_check(
            "Identifiants de transactions",
            duplicates == 0,
            f"{duplicates} doublon(s)."
        )

        # ====================================================
        # 8. ANALYSE DES MONTANTS
        # ====================================================

        add_report("\n## 6. ANALYSE DES MONTANTS")

        amounts = conn.execute(text("""
            SELECT
                MIN(amount),
                MAX(amount),
                AVG(amount),
                PERCENTILE_CONT(0.5)
                    WITHIN GROUP (ORDER BY amount),
                COUNT(*) FILTER (WHERE amount <= 0)
            FROM fact_transactions;
        """)).fetchone()

        add_report(f"Montant minimum : {amounts[0]}")
        add_report(f"Montant maximum : {amounts[1]}")
        add_report(f"Montant moyen : {amounts[2]:.2f}")
        add_report(f"Montant médian : {amounts[3]:.2f}")

        record_check(
            "Montants positifs",
            amounts[4] == 0,
            f"{amounts[4]} montant(s) nul(s) ou négatif(s)."
        )

        # ====================================================
        # 9. INTEGRITE DES RELATIONS
        # ====================================================

        add_report("\n## 7. INTEGRITE DES RELATIONS")

        relations = conn.execute(text("""
            SELECT
                COUNT(*) FILTER (
                    WHERE t.time_id IS NULL
                ),
                COUNT(*) FILTER (
                    WHERE ty.type_id IS NULL
                ),
                COUNT(*) FILTER (
                    WHERE ce.orig_account_id IS NULL
                ),
                COUNT(*) FILTER (
                    WHERE cd.dest_account_id IS NULL
                )
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

        relation_names = [
            "Temps absent",
            "Type absent",
            "Emetteur absent",
            "Destinataire absent"
        ]

        for name, value in zip(relation_names, relations):

            record_check(
                name,
                value == 0,
                f"{value} relation(s) non résolue(s)."
            )

        # ====================================================
        # 10. DISTRIBUTION DES CLASSES
        # ====================================================

        add_report("\n## 8. DISTRIBUTION DES CLASSES")

        classes = conn.execute(text("""
            SELECT
                is_fraud,
                COUNT(*)
            FROM fact_transactions
            GROUP BY is_fraud
            ORDER BY is_fraud;
        """)).fetchall()

        for label, count in classes:

            percentage = count / total * 100 if total else 0

            name = "Fraudes" if label == 1 else "Transactions normales"

            add_report(
                f"- {name} : {count:,} ({percentage:.2f} %)"
            )

        fraud_count = conn.execute(text("""
            SELECT COUNT(*)
            FROM fact_transactions
            WHERE is_fraud = 1;
        """)).scalar()

        fraud_rate = fraud_count / total * 100 if total else 0

        add_report(f"\nTaux global de fraude : {fraud_rate:.2f} %")

        # ====================================================
        # 11. FRAUDES PAR TYPE
        # ====================================================

        add_report("\n## 9. FRAUDES PAR TYPE D'OPERATION")

        fraud_by_type = conn.execute(text("""
            SELECT
                ty.code_type,
                COUNT(*) AS total,
                COUNT(*) FILTER (
                    WHERE f.is_fraud = 1
                ) AS frauds,
                ROUND(
                    100.0 * COUNT(*) FILTER (
                        WHERE f.is_fraud = 1
                    ) / NULLIF(COUNT(*), 0),
                    2
                ) AS fraud_rate
            FROM fact_transactions f

            JOIN dim_type_operation ty
                ON f.type_id = ty.type_id

            GROUP BY ty.code_type
            ORDER BY fraud_rate DESC;
        """)).fetchall()

        for row in fraud_by_type:

            add_report(
                f"- {row[0]} : {row[1]:,} transactions | "
                f"{row[2]:,} fraudes | {row[3]} %"
            )

        # ====================================================
        # 12. ANALYSE TEMPORELLE
        # ====================================================

        add_report("\n## 10. ANALYSE TEMPORELLE")

        temporal = conn.execute(text("""
            SELECT
                t.step,
                COUNT(*) AS total,
                COUNT(*) FILTER (
                    WHERE f.is_fraud = 1
                ) AS frauds
            FROM fact_transactions f

            JOIN dim_temps t
                ON f.time_id = t.time_id

            GROUP BY t.step
            ORDER BY t.step;
        """)).fetchall()

        fraud_free_steps = sum(
            1 for row in temporal if row[2] == 0
        )

        add_report(f"Nombre de périodes : {len(temporal)}")

        if temporal:

            add_report(f"Step minimum : {temporal[0][0]}")
            add_report(f"Step maximum : {temporal[-1][0]}")

        add_report(
            f"Périodes sans fraude : {fraud_free_steps}"
        )

        add_report("\nDix premières périodes :")

        for row in temporal[:10]:

            add_report(
                f"Step {row[0]} | "
                f"Transactions : {row[1]} | "
                f"Fraudes : {row[2]}"
            )

        add_report("\nDix dernières périodes :")

        for row in temporal[-10:]:

            add_report(
                f"Step {row[0]} | "
                f"Transactions : {row[1]} | "
                f"Fraudes : {row[2]}"
            )

        # ====================================================
        # 13. ISFLAGGEDFRAUD
        # ====================================================

        add_report("\n## 11. ANALYSE DE ISFLAGGEDFRAUD")

        flagged = conn.execute(text("""
            SELECT
                is_flagged_fraud,
                is_fraud,
                COUNT(*)
            FROM fact_transactions
            GROUP BY is_flagged_fraud, is_fraud
            ORDER BY is_flagged_fraud, is_fraud;
        """)).fetchall()

        for row in flagged:

            add_report(
                f"is_flagged_fraud={row[0]} | "
                f"is_fraud={row[1]} | "
                f"Nombre : {row[2]:,}"
            )

        flagged_total = conn.execute(text("""
            SELECT COUNT(*)
            FROM fact_transactions
            WHERE is_flagged_fraud = 1;
        """)).scalar()

        add_report(
            f"\nTransactions signalées par le système : "
            f"{flagged_total:,}"
        )

        observations.append(
            "is_flagged_fraud est conservée pour l'analyse, "
            "mais exclue initialement des variables explicatives."
        )

        # ====================================================
        # 14. VARIABLES INTERDITES
        # ====================================================

        add_report("\n## 12. VERIFICATION DES VARIABLES INTERDITES")

        forbidden = {
            "oldbalanceOrg",
            "newbalanceOrig",
            "oldbalanceDest",
            "newbalanceDest"
        }

        all_columns = set()

        for table in expected_tables:

            columns = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = :table;
            """), {"table": table}).scalars().all()

            all_columns.update(columns)

        found_forbidden = forbidden.intersection(all_columns)

        record_check(
            "Colonnes de soldes interdites",
            len(found_forbidden) == 0,
            f"Colonnes trouvées : {found_forbidden or 'Aucune'}"
        )

        # ====================================================
        # 15. ECHANTILLONNAGE
        # ====================================================

        add_report("\n## 13. METHODE D'ECHANTILLONNAGE")

        add_report(
            "Selon l'analyse du code etl_pipeline.py :"
        )

        add_report(
            "- Toutes les transactions frauduleuses sont "
            "sélectionnées avant le nettoyage."
        )

        add_report(
            "- Les transactions légitimes sont échantillonnées "
            "par type d'opération."
        )

        add_report(
            "- Le tirage utilise random_state=42."
        )

        add_report(
            "- Les transactions dont le montant est inférieur "
            "ou égal à zéro sont ensuite supprimées."
        )

        add_report(
            "- La proportion de fraudes dans le DWH est supérieure "
            "à celle du dataset original."
        )

        observations.append(
            "Les taux d'échantillonnage exacts par classe et par type "
            "doivent être calculés à partir du dataset original. "
            "Le DWH seul ne permet pas de les reconstituer."
        )

        # ====================================================
        # 16. SYNTHESE
        # ====================================================

        add_report("\n## 14. SYNTHESE GENERALE")

        add_report(f"Transactions analysées : {total:,}")

        add_report(f"Transactions frauduleuses : {fraud_count:,}")

        add_report(f"Taux de fraude : {fraud_rate:.2f} %")

        add_report(f"Nombre d'anomalies détectées : {len(anomalies)}")

        if anomalies:

            add_report("\n### Anomalies à examiner")

            for anomaly in anomalies:
                add_report(f"- {anomaly}")

        else:

            add_report(
                "\nAucune anomalie détectée dans les contrôles exécutés."
            )

        add_report("\n### Observations méthodologiques")

        for observation in observations:
            add_report(f"- {observation}")

        add_report("\n---")

        add_report(
            "Fin de l'audit du Data Warehouse PaySim."
        )

    # ========================================================
    # 17. GENERATION DU RAPPORT
    # ========================================================

    with open(REPORT_PATH, "w", encoding="utf-8") as file:

        file.write("\n".join(report))

    print("\n============================================")
    print("AUDIT TERMINE")
    print("============================================")

    print(f"Rapport généré : {REPORT_PATH}")

except Exception as error:

    print("\nERREUR PENDANT L'AUDIT")
    print(error)

    raise

finally:

    engine.dispose()