-- ====================================================================
-- Schéma en étoile pour le DWH Mobile Money PaySim (PostgreSQL)
-- Sujet 1 : Détection de fraude et tableau de bord
-- ====================================================================

-- 1. Nettoyage préalable (si réinitialisation)
DROP TABLE IF EXISTS fact_transactions CASCADE;
DROP TABLE IF EXISTS dim_temps CASCADE;
DROP TABLE IF EXISTS dim_type_operation CASCADE;
DROP TABLE IF EXISTS dim_compte_emetteur CASCADE;
DROP TABLE IF EXISTS dim_compte_destinataire CASCADE;

-- 2. Dimension : Type d'opération
CREATE TABLE dim_type_operation (
    type_id SERIAL PRIMARY KEY,
    code_type VARCHAR(20) NOT NULL UNIQUE,
    categorie VARCHAR(30),
    description TEXT
);

-- Insertion des 5 types d'opérations PaySim
INSERT INTO dim_type_operation (code_type, categorie, description) VALUES
('CASH_IN', 'Dépôt', 'Dépôt d''argent liquide sur le compte client'),
('CASH_OUT', 'Retrait', 'Retrait d''argent liquide depuis le compte client'),
('DEBIT', 'Paiement', 'Prélèvement / débit bancaire direct'),
('PAYMENT', 'Achat', 'Paiement direct de biens ou services à un commerçant'),
('TRANSFER', 'Virement', 'Transfert d''argent de client à client ou compte à compte');

-- 3. Dimension : Temps (dérivée du step PaySim : 1 step = 1 heure)
CREATE TABLE dim_temps (
    time_id INT PRIMARY KEY,              -- step (1 à 744)
    step INT NOT NULL,
    jour INT NOT NULL,                    -- Jour du mois (1 à 31)
    heure INT NOT NULL,                   -- Heure de la journée (0 à 23)
    tranche_horaire VARCHAR(20) NOT NULL, -- Nuit (0-5), Matin (6-11), Après-midi (12-17), Soir (18-23)
    type_jour VARCHAR(15) NOT NULL        -- Semaine / Week-end
);

-- 4. Dimension : Compte Émetteur (nameOrig)
CREATE TABLE dim_compte_emetteur (
    orig_account_id SERIAL PRIMARY KEY,
    account_number VARCHAR(30) NOT NULL UNIQUE,
    account_type VARCHAR(15) NOT NULL     -- 'Client' (C...) ou 'Commerçant' (M...)
);

-- 5. Dimension : Compte Destinataire (nameDest)
CREATE TABLE dim_compte_destinataire (
    dest_account_id SERIAL PRIMARY KEY,
    account_number VARCHAR(30) NOT NULL UNIQUE,
    account_type VARCHAR(15) NOT NULL     -- 'Client' (C...) ou 'Commerçant' (M...)
);

-- 6. Table de Faits : Transactions
CREATE TABLE fact_transactions (
    transaction_id BIGSERIAL PRIMARY KEY,
    time_id INT NOT NULL REFERENCES dim_temps(time_id),
    type_id INT NOT NULL REFERENCES dim_type_operation(type_id),
    orig_account_id INT NOT NULL REFERENCES dim_compte_emetteur(orig_account_id),
    dest_account_id INT NOT NULL REFERENCES dim_compte_destinataire(dest_account_id),
    amount NUMERIC(15, 2) NOT NULL,
    is_fraud SMALLINT NOT NULL DEFAULT 0,          -- 1 = Fraude, 0 = Légitime
    is_flagged_fraud SMALLINT NOT NULL DEFAULT 0   -- 1 = Flaggué par le système existant
);

-- 7. Index pour optimiser les performances des requêtes Power BI
CREATE INDEX idx_fact_time ON fact_transactions(time_id);
CREATE INDEX idx_fact_type ON fact_transactions(type_id);
CREATE INDEX idx_fact_fraud ON fact_transactions(is_fraud);
CREATE INDEX idx_fact_amount ON fact_transactions(amount);
