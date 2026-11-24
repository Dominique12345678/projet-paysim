# RAPPORT D'AUDIT DU DATA WAREHOUSE PAYSIM

Date de l'audit : 24/11/2026 11:30:37

---


## 1. CONNEXION A POSTGRESQL
Connexion PostgreSQL réussie.
Version : PostgreSQL 18.7 (Debian 18.7-1.pgdg12+5) on x86_64-pc-linux-gnu, compiled by gcc (Debian 12.2.0-14+deb12u1) 12.2.0, 64-bit

## 2. STRUCTURE DU DATA WAREHOUSE
- **Table dim_compte_destinataire : OK** 
- **Table dim_compte_emetteur : OK** 
- **Table dim_temps : OK** 
- **Table dim_type_operation : OK** 
- **Table fact_transactions : OK** 

### Vérification des colonnes
- **Colonnes de fact_transactions : OK** Colonnes manquantes : Aucune
- **Colonnes de dim_temps : OK** Colonnes manquantes : Aucune
- **Colonnes de dim_type_operation : OK** Colonnes manquantes : Aucune
- **Colonnes de dim_compte_emetteur : OK** Colonnes manquantes : Aucune
- **Colonnes de dim_compte_destinataire : OK** Colonnes manquantes : Aucune

## 3. VOLUME DES DONNEES
Nombre de transactions : 299,983
- **Volume des transactions : OK** 299,983 lignes présentes.

## 4. VALEURS MANQUANTES
- **Valeurs manquantes - amount : OK** 0 valeur(s) manquante(s).
- **Valeurs manquantes - time_id : OK** 0 valeur(s) manquante(s).
- **Valeurs manquantes - type_id : OK** 0 valeur(s) manquante(s).
- **Valeurs manquantes - orig_account_id : OK** 0 valeur(s) manquante(s).
- **Valeurs manquantes - dest_account_id : OK** 0 valeur(s) manquante(s).
- **Valeurs manquantes - is_fraud : OK** 0 valeur(s) manquante(s).
- **Valeurs manquantes - is_flagged_fraud : OK** 0 valeur(s) manquante(s).

## 5. DOUBLONS
- **Identifiants de transactions : OK** 0 doublon(s).

## 6. ANALYSE DES MONTANTS
Montant minimum : 0.23
Montant maximum : 60642003.00
Montant moyen : 213759.41
Montant médian : 79202.27
- **Montants positifs : OK** 0 montant(s) nul(s) ou négatif(s).

## 7. INTEGRITE DES RELATIONS
- **Temps absent : OK** 0 relation(s) non résolue(s).
- **Type absent : OK** 0 relation(s) non résolue(s).
- **Emetteur absent : OK** 0 relation(s) non résolue(s).
- **Destinataire absent : OK** 0 relation(s) non résolue(s).

## 8. DISTRIBUTION DES CLASSES
- Transactions normales : 291,786 (97.27 %)
- Fraudes : 8,197 (2.73 %)

Taux global de fraude : 2.73 %

## 9. FRAUDES PAR TYPE D'OPERATION
- TRANSFER : 28,379 transactions | 4,097 fraudes | 14.44 %
- CASH_OUT : 106,654 transactions | 4,100 fraudes | 3.84 %
- CASH_IN : 64,253 transactions | 0 fraudes | 0.00 %
- DEBIT : 1,903 transactions | 0 fraudes | 0.00 %
- PAYMENT : 98,794 transactions | 0 fraudes | 0.00 %

## 10. ANALYSE TEMPORELLE
Nombre de périodes : 743
Step minimum : 1
Step maximum : 743
Périodes sans fraude : 2

Dix premières périodes :
Step 1 | Transactions : 148 | Fraudes : 16
Step 2 | Transactions : 56 | Fraudes : 8
Step 3 | Transactions : 35 | Fraudes : 4
Step 4 | Transactions : 42 | Fraudes : 10
Step 5 | Transactions : 38 | Fraudes : 6
Step 6 | Transactions : 95 | Fraudes : 22
Step 7 | Transactions : 330 | Fraudes : 12
Step 8 | Transactions : 997 | Fraudes : 12
Step 9 | Transactions : 1776 | Fraudes : 19
Step 10 | Transactions : 1658 | Fraudes : 11

Dix dernières périodes :
Step 734 | Transactions : 8 | Fraudes : 8
Step 735 | Transactions : 12 | Fraudes : 12
Step 736 | Transactions : 14 | Fraudes : 14
Step 737 | Transactions : 10 | Fraudes : 10
Step 738 | Transactions : 10 | Fraudes : 10
Step 739 | Transactions : 10 | Fraudes : 10
Step 740 | Transactions : 6 | Fraudes : 6
Step 741 | Transactions : 21 | Fraudes : 21
Step 742 | Transactions : 14 | Fraudes : 14
Step 743 | Transactions : 8 | Fraudes : 8

## 11. ANALYSE DE ISFLAGGEDFRAUD
is_flagged_fraud=0 | is_fraud=0 | Nombre : 291,786
is_flagged_fraud=0 | is_fraud=1 | Nombre : 8,181
is_flagged_fraud=1 | is_fraud=1 | Nombre : 16

Transactions signalées par le système : 16

## 12. VERIFICATION DES VARIABLES INTERDITES
- **Colonnes de soldes interdites : OK** Colonnes trouvées : Aucune

## 13. METHODE D'ECHANTILLONNAGE
Selon l'analyse du code etl_pipeline.py :
- Toutes les transactions frauduleuses sont sélectionnées avant le nettoyage.
- Les transactions légitimes sont échantillonnées par type d'opération.
- Le tirage utilise random_state=42.
- Les transactions dont le montant est inférieur ou égal à zéro sont ensuite supprimées.
- La proportion de fraudes dans le DWH est supérieure à celle du dataset original.

## 14. SYNTHESE GENERALE
Transactions analysées : 299,983
Transactions frauduleuses : 8,197
Taux de fraude : 2.73 %
Nombre d'anomalies détectées : 0

Aucune anomalie détectée dans les contrôles exécutés.

### Observations méthodologiques
- is_flagged_fraud est conservée pour l'analyse, mais exclue initialement des variables explicatives.
- Les taux d'échantillonnage exacts par classe et par type doivent être calculés à partir du dataset original. Le DWH seul ne permet pas de les reconstituer.

---
Fin de l'audit du Data Warehouse PaySim.