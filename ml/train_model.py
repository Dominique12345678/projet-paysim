"""
Script d'entrainement et d'evaluation Machine Learning (Mobile Money Fraude).
Permet d'executer l'ensemble du pipeline ML depuis la ligne de commande.
Charge les donnees depuis PostgreSQL Render (avec fallback sur le fichier local).
"""

import os
import sys
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    average_precision_score
)

print("="*70)
print("DEMARRAGE DU PIPELINE MACHINE LEARNING - DETECTION DE FRAUDE")
print("="*70)

# 1. Chargement des donnees (Render PostgreSQL avec fallback)
load_dotenv()
database_url = os.getenv("DATABASE_URL")

query = """
SELECT 
    f.amount,
    f.is_fraud,
    f.is_flagged_fraud,
    t.code_type AS transaction_type,
    d.heure,
    d.tranche_horaire,
    d.type_jour,
    orig.account_type AS orig_type,
    dest.account_type AS dest_type
FROM fact_transactions f
JOIN dim_type_operation t ON f.type_id = t.type_id
JOIN dim_temps d ON f.time_id = d.time_id
JOIN dim_compte_emetteur orig ON f.orig_account_id = orig.orig_account_id
JOIN dim_compte_destinataire dest ON f.dest_account_id = dest.dest_account_id;
"""

df = None
if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        
    try:
        print("Chargement des donnees depuis PostgreSQL Render (DWH)...")
        engine = create_engine(database_url, connect_args={"sslmode": "require"})
        df = pd.read_sql(query, engine)
        print(f"Charge depuis Render : {len(df):,} transactions.")
    except Exception as e:
        print(f"Connexion distante Render non accessible ({e}). Basculement sur source locale...")

if df is None or len(df) == 0:
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "paysim.csv")
    print(f"Chargement depuis le fichier local {csv_path}...")
    cols = ['step', 'type', 'amount', 'nameOrig', 'nameDest', 'isFraud', 'isFlaggedFraud']
    raw_df = pd.read_csv(csv_path, usecols=cols)
    
    # Echantillonnage identique a l'ETL (100% fraudes + echantillon legitime)
    df_frauds = raw_df[raw_df['isFraud'] == 1].copy()
    df_legit = raw_df[raw_df['isFraud'] == 0].sample(n=291787, random_state=42).copy()
    s_df = pd.concat([df_frauds, df_legit], ignore_index=True).sample(frac=1.0, random_state=42)
    
    s_df['heure'] = (s_df['step'] - 1) % 24
    s_df['jour'] = ((s_df['step'] - 1) // 24) + 1
    s_df['type_jour'] = s_df['jour'].apply(lambda j: 'Week-end' if ((j - 1) % 7) in [5, 6] else 'Semaine')
    
    def get_tranche(h):
        if h < 6: return 'Nuit'
        elif h < 12: return 'Matin'
        elif h < 18: return 'Apres-midi'
        else: return 'Soir'
    s_df['tranche_horaire'] = s_df['heure'].apply(get_tranche)
    s_df['orig_type'] = s_df['nameOrig'].apply(lambda x: 'Commercant' if str(x).startswith('M') else 'Client')
    s_df['dest_type'] = s_df['nameDest'].apply(lambda x: 'Commercant' if str(x).startswith('M') else 'Client')
    
    s_df.rename(columns={'type': 'transaction_type', 'isFraud': 'is_fraud', 'isFlaggedFraud': 'is_flagged_fraud'}, inplace=True)
    df = s_df[['amount', 'is_fraud', 'is_flagged_fraud', 'transaction_type', 'heure', 'tranche_horaire', 'type_jour', 'orig_type', 'dest_type']].copy()
    print(f"Charge depuis local : {len(df):,} transactions.")

print(f"Total des donnees : {len(df):,} lignes (Fraudes : {df['is_fraud'].sum():,})")

# 2. Feature Engineering (Sans fuite de soldes)
print("\nFeature Engineering sans fuite de donnees...")
df_ml = df.copy()
df_ml['log_amount'] = np.log1p(df_ml['amount'])
df_ml['is_night'] = (df_ml['heure'] < 6).astype(int)
df_ml['is_high_amount'] = (df_ml['amount'] >= 200000).astype(int)
df_ml['is_weekend'] = (df_ml['type_jour'] == 'Week-end').astype(int)
df_ml['dest_is_merchant'] = (df_ml['dest_type'] == 'Commercant').astype(int)

df_ml = pd.get_dummies(df_ml, columns=['transaction_type', 'tranche_horaire'], drop_first=True)

features_to_drop = ['amount', 'is_fraud', 'type_jour', 'orig_type', 'dest_type']
X = df_ml.drop(columns=features_to_drop)
y = df_ml['is_fraud'].astype(int)

# 3. Train / Test Split Stratifie
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y
)
print(f"Train set : {X_train.shape[0]:,} | Test set : {X_test.shape[0]:,}")

# Standardisation pour la regression logistique
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 4. Modele 1 : Regression Logistique (Baseline)
print("\n" + "="*50)
print("1. REGRESSION LOGISTIQUE (BASELINE)")
print("="*50)
lr_model = LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42)
lr_model.fit(X_train_scaled, y_train)

y_pred_lr = lr_model.predict(X_test_scaled)
y_proba_lr = lr_model.predict_proba(X_test_scaled)[:, 1]

print(classification_report(y_test, y_pred_lr, digits=4))
print(f"ROC-AUC : {roc_auc_score(y_test, y_proba_lr):.4f}")
print(f"PR-AUC  : {average_precision_score(y_test, y_proba_lr):.4f}")

# 5. Modele 2 : Random Forest
print("\n" + "="*50)
print("2. RANDOM FOREST CLASSIFIER")
print("="*50)
rf_model = RandomForestClassifier(n_estimators=100, max_depth=12, class_weight='balanced', random_state=42, n_jobs=-1)
rf_model.fit(X_train, y_train)

y_pred_rf = rf_model.predict(X_test)
y_proba_rf = rf_model.predict_proba(X_test)[:, 1]

print(classification_report(y_test, y_pred_rf, digits=4))
print(f"ROC-AUC : {roc_auc_score(y_test, y_proba_rf):.4f}")
print(f"PR-AUC  : {average_precision_score(y_test, y_proba_rf):.4f}")

# 6. Matrice de confusion detaillee
cm_rf = confusion_matrix(y_test, y_pred_rf)
tn, fp, fn, tp = cm_rf.ravel()
print("\nMatrice de confusion Random Forest :")
print(f"  Vrais Negatifs (Legitimes bien predits)   : {tn:,}")
print(f"  Faux Positifs (Clients bloques a tort)   : {fp:,}")
print(f"  Faux Negatifs (Fraudes non detectees)    : {fn:,}")
print(f"  Vrais Positifs (Fraudes interceptees)    : {tp:,}")
print(f"  Rappel (Recall) sur la fraude            : {tp / (tp + fn) * 100:.2f}%")
print(f"  Precision sur les alertes                : {tp / (tp + fp) * 100:.2f}%")

# 7. Reglage du seuil pour la recommandation business
print("\n" + "="*50)
print("3. ANALYSE DU SEUIL DE DECISION (RECOMMANDATION)")
print("="*50)
for threshold in [0.3, 0.4, 0.5, 0.6, 0.7]:
    preds = (y_proba_rf >= threshold).astype(int)
    cm = confusion_matrix(y_test, preds)
    _tn, _fp, _fn, _tp = cm.ravel()
    rec = _tp / (_tp + _fn)
    prec = _tp / (_tp + _fp) if (_tp + _fp) > 0 else 0
    print(f"Seuil {threshold:.1f} -> Rappel : {rec*100:.2f}% | Precision : {prec*100:.2f}% | Faux Positifs : {_fp:,}")

print("="*70)
print("PIPELINE MACHINE LEARNING EXECUTE AVEC SUCCES !")
print("="*70)
