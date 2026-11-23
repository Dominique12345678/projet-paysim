# 📖 Dictionnaire des Données - Data Warehouse PaySim

Ce document décrit chaque table et colonne du schéma en étoile déployé dans la base PostgreSQL sur Render.

---

## 1. Table de Faits : `fact_transactions`

Enregistre l'ensemble des événements de transactions financières du mobile money.

| Nom de la colonne | Type SQL | Contrainte | Description / Rôle métier | Exemple |
| :--- | :--- | :--- | :--- | :--- |
| `transaction_id` | `BIGSERIAL` | `PRIMARY KEY` | Identifiant technique unique auto-incrémenté de la transaction. | `1` |
| `time_id` | `INT` | `FOREIGN KEY` $\rightarrow$ `dim_temps.time_id` | Clé temporelle correspondant à l'heure de la transaction (1 à 744). | `355` |
| `type_id` | `INT` | `FOREIGN KEY` $\rightarrow$ `dim_type_operation.type_id` | Clé identifiant le type d'opération financière. | `2` |
| `orig_account_id` | `INT` | `FOREIGN KEY` $\rightarrow$ `dim_compte_emetteur.orig_account_id` | Clé du compte client ayant émis la transaction. | `299960` |
| `dest_account_id` | `INT` | `FOREIGN KEY` $\rightarrow$ `dim_compte_destinataire.dest_account_id` | Clé du compte bénéficiaire ayant reçu la transaction. | `248326` |
| `amount` | `NUMERIC(15,2)` | `NOT NULL` | Montant de la transaction en devise locale. | `131845.80` |
| `is_fraud` | `SMALLINT` | `NOT NULL, DEFAULT 0` | Indicateur de fraude réelle (`1` = Fraude confirmée, `0` = Transaction légitime). | `1` |
| `is_flagged_fraud` | `SMALLINT` | `NOT NULL, DEFAULT 0` | Indicateur d'alerte levé par le système classique (transactions > 200 000). | `0` |

---

## 2. Dimension : `dim_type_operation`

Référentiel des types d'opérations bancaires disponibles dans le service mobile money.

| Nom de la colonne | Type SQL | Contrainte | Description / Rôle métier | Exemple |
| :--- | :--- | :--- | :--- | :--- |
| `type_id` | `SERIAL` | `PRIMARY KEY` | Clé technique unique du type d'opération. | `1` |
| `code_type` | `VARCHAR(20)` | `NOT NULL, UNIQUE` | Code métier de l'opération dans le système. | `CASH_OUT` |
| `categorie` | `VARCHAR(30)` | `NULLABLE` | Catégorie fonctionnelle (Dépôt, Retrait, Achat, Virement). | `Retrait` |
| `description` | `TEXT` | `NULLABLE` | Description explicative détaillée de l'opération. | `Retrait d'argent liquide depuis le compte` |

### Données de référence :
* `1` : `CASH_IN` (Dépôt)
* `2` : `CASH_OUT` (Retrait d'espèces) - *Cible majeure des fraudes*
* `3` : `DEBIT` (Prélèvement direct)
* `4` : `PAYMENT` (Achat direct chez un commerçant)
* `5` : `TRANSFER` (Virement compte à compte) - *Cible majeure des fraudes*

---

## 3. Dimension : `dim_temps`

Modélisation du calendrier horaire dérivé du `step` (744 heures au total, soit 31 jours).

| Nom de la colonne | Type SQL | Contrainte | Description / Rôle métier | Exemple |
| :--- | :--- | :--- | :--- | :--- |
| `time_id` | `INT` | `PRIMARY KEY` | Identifiant temporel (1 à 744). | `42` |
| `step` | `INT` | `NOT NULL` | Numéro d'heure séquentielle depuis le début de la simulation. | `42` |
| `jour` | `INT` | `NOT NULL` | Jour du mois simulé (1 à 31), calculé via `((step - 1) // 24) + 1`. | `2` |
| `heure` | `INT` | `NOT NULL` | Heure exacte de la journée (0 à 23), calculée via `(step - 1) % 24`. | `17` |
| `tranche_horaire` | `VARCHAR(20)` | `NOT NULL` | Période du jour : `Nuit` (0-5h), `Matin` (6-11h), `Après-midi` (12-17h), `Soir` (18-23h). | `Après-midi` |
| `type_jour` | `VARCHAR(15)` | `NOT NULL` | Typologie du jour : `Semaine` ou `Week-end`. | `Semaine` |

---

## 4. Dimension : `dim_compte_emetteur`

Référentiel des comptes ayant initié une transaction.

| Nom de la colonne | Type SQL | Contrainte | Description / Rôle métier | Exemple |
| :--- | :--- | :--- | :--- | :--- |
| `orig_account_id` | `SERIAL` | `PRIMARY KEY` | Clé technique unique du compte émetteur. | `1054` |
| `account_number` | `VARCHAR(30)` | `NOT NULL, UNIQUE` | Numéro/identifiant masqué du compte émetteur. | `C1234567890` |
| `account_type` | `VARCHAR(15)` | `NOT NULL` | Statut du compte : `Client` (commence par `C`) ou `Commerçant` (commence par `M`). | `Client` |

---

## 5. Dimension : `dim_compte_destinataire`

Référentiel des comptes ayant reçu une transaction.

| Nom de la colonne | Type SQL | Contrainte | Description / Rôle métier | Exemple |
| :--- | :--- | :--- | :--- | :--- |
| `dest_account_id` | `SERIAL` | `PRIMARY KEY` | Clé technique unique du compte destinataire. | `542` |
| `account_number` | `VARCHAR(30)` | `NOT NULL, UNIQUE` | Numéro/identifiant masqué du compte destinataire. | `M9876543210` |
| `account_type` | `VARCHAR(15)` | `NOT NULL` | Statut du compte : `Client` (commence par `C`) ou `Commerçant` (commence par `M`). | `Commerçant` |
