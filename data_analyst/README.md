# README détaillé — Ma contribution Data Analyst (PaySim)

**Projet :** Big Data LBS — Analyse des transactions Mobile Money et des fraudes.  
**Rôle :** Data Analyst / restitution décisionnelle.  
**État :** deux pages Power BI réalisées, fichier PBIX sauvegardé ; finition du format de la carte « Nombre de fraudes » reportée.

## 1. Mission et objectif

Transformer les données préparées par le Data Engineer en indicateurs compréhensibles pour répondre à ces questions : combien de transactions ? combien de fraudes ? quels types d'opérations sont concernés ? à quelles heures observe-t-on des variations ? quelle part des montants est associée à des fraudes ? Il s'agit d'**analyse descriptive**, et non d'un modèle de prédiction de fraude.

## 2. Point de départ et provenance

Le Data Engineer a fourni un entrepôt PostgreSQL hébergé sur Render. Les fichiers examinés dans le dépôt du groupe sont `sql/schema_dwh.sql`, `etl/etl_pipeline.py`, `etl/populate_dim_temps.py`, `docs/architecture.md` et `docs/DOCUMENTATION_DATA_ENGINEER.md`.

Le pipeline lit le CSV PaySim et conserve `step`, `type`, `amount`, `nameOrig`, `nameDest`, `isFraud`, `isFlaggedFraud`. Il sélectionne les fraudes, échantillonne les transactions légitimes par type d'opération (`random_state=42`), mélange les données, retire les montants non positifs et charge les tables PostgreSQL avec `COPY`. Le filtrage `amount > 0` intervient **après** l'échantillonnage : le total chargé est **299 983** plutôt que la cible de 300 000.

**Précaution :** le code conserve initialement toutes les fraudes avant le filtrage des montants ; le nombre final est de **8 197**. Le document du Data Engineer mentionne ailleurs **8 213** fraudes dans la source. Il ne faut donc pas écrire que 100 % des fraudes brutes sont présentes dans le DWH final sans vérification supplémentaire.

## 3. Connexion à Power BI — procédure réalisée

1. Ouvrir Power BI Desktop.
2. **Accueil > Obtenir les données > PostgreSQL**.
3. Renseigner l'hôte et le nom de base Render communiqués par le Data Engineer ; s'authentifier sans exposer le mot de passe dans Git.
4. Importer les cinq tables du schéma `public`.
5. Vérifier le nombre de lignes, les types de données et les relations dans la **Vue Modèle**.
6. Créer les mesures DAX, puis les graphiques dans la **Vue Rapport**.
7. Sauvegarder le rapport sous `PaySim_Analyse_Fraude_LBS.pbix`.

**Sécurité :** jamais de mot de passe ni d'URL PostgreSQL complète contenant un secret dans le README, les captures ou le dépôt Git.

## 4. Modèle de données

| Table | Rôle | Colonnes utiles |
|---|---|---|
| `public fact_transactions` | Table de faits : une ligne par transaction | `transaction_id`, `time_id`, `type_id`, `orig_account_id`, `dest_account_id`, `amount`, `is_fraud`, `is_flagged_fraud` |
| `public dim_temps` | Analyse temporelle | `time_id`, `step`, `jour`, `heure`, `tranche_horaire`, `type_jour` |
| `public dim_type_operation` | Classification des opérations | `type_id`, `code_type`, `categorie` |
| `public dim_compte_emetteur` | Émetteur | `orig_account_id`, `account_number`, `account_type` |
| `public dim_compte_destinataire` | Destinataire | `dest_account_id`, `account_number`, `account_type` |

Les quatre dimensions se relient à la table de faits par leurs clés, en relations **1 vers plusieurs**, avec filtrage de la dimension vers les faits. Cela permet aux catégories d'opération et aux heures de filtrer correctement les mesures. Le schéma a été conçu en amont par le Data Engineer ; ma contribution a consisté à **l'importer, vérifier et exploiter dans Power BI**, et non à le créer dans PostgreSQL.

Les types sont : `CASH_IN` = Dépôt, `CASH_OUT` = Retrait, `DEBIT` = Paiement, `PAYMENT` = Achat, `TRANSFER` = Virement.

## 5. Mesures DAX créées

```dax
Total Transactions =
COUNTROWS('public fact_transactions')

Nombre de fraudes =
CALCULATE(
    COUNTROWS('public fact_transactions'),
    'public fact_transactions'[is_fraud] = 1
)

Taux de fraude =
DIVIDE([Nombre de fraudes], [Total Transactions], 0)

Montant total =
SUM('public fact_transactions'[amount])

Montant des fraudes =
CALCULATE(
    SUM('public fact_transactions'[amount]),
    'public fact_transactions'[is_fraud] = 1
)

Part financière des fraudes =
DIVIDE([Montant des fraudes], [Montant total], 0)
```

**Explication pédagogique :**

- `COUNTROWS` compte les lignes de transactions dans le contexte des filtres.
- `CALCULATE` modifie le contexte pour retenir seulement `is_fraud = 1`.
- `SUM` additionne les montants ; l'unité monétaire de PaySim n'est pas à présenter comme une devise réelle vérifiée.
- `DIVIDE` évite les erreurs de division par zéro. Les deux ratios sont formatés en **pourcentage** dans Power BI ; on ne multiplie pas encore par 100 dans le DAX.
- Les mesures se recalculent lorsqu'un filtre sur le type ou l'heure est appliqué.

## 6. Résultats vérifiés dans Power BI

| Indicateur | Valeur |
|---|---:|
| Transactions | **299 983** |
| Fraudes | **8 197** |
| Taux de fraude | **2,73 %** |
| Montant cumulé | **64,12 Md** (affichage arrondi) |
| Montant des transactions frauduleuses | **12,06 Md** (affichage arrondi) |
| Part financière des fraudes | **18,80 %** (mesure exacte affichée) |

**Interprétation :** la part des montants associés aux fraudes (18,80 %) est supérieure à leur fréquence en nombre (2,73 %) : dans cet échantillon, les transactions frauduleuses sont en moyenne plus importantes. Ces montants ne sont **pas** nécessairement des pertes effectivement subies.

## 7. Page 1 — Vue d'ensemble

- Quatre cartes : transactions, fraudes, taux de fraude, montant total.
- Histogramme des volumes par catégorie : Retrait ~107k, Achat ~99k, Dépôt ~64k, Virement ~28k, Paiement ~2k.
- Histogramme du taux de fraude par catégorie : Virement **14,44 %**, Retrait **3,84 %** ; aucune fraude observée dans les autres catégories de l'échantillon.
- Courbe des transactions par heure : pic à **18h avec 30 081 transactions**.

**Lecture :** les retraits dominent en volume ; les virements ont le taux de fraude observé le plus élevé parmi les catégories. Un taux de fraude n'est pas la même chose qu'un nombre absolu de fraudes.

## 8. Page 2 — Analyse détaillée des fraudes

- Trois cartes : nombre de fraudes, montant des fraudes, part financière des fraudes.
- Histogramme des fraudes par type : retraits et virements, environ **4,1k chacun**.
- Courbe du taux de fraude par heure : maximum à **4h, 88,41 %**, dans l'échantillon.
- Courbe du nombre de fraudes par heure : volumes relativement stables, contrairement aux volumes totaux de transactions.
- Tableau de contrôle par heure et encadré de conclusion.

### Tableau horaire vérifié

| Heure | Transactions | Fraudes | Taux |
|---:|---:|---:|---:|
| 00h | 1 566 | 358 | 22 86 % |
| 01h | 787 | 371 | 47 14 % |
| 02h | 402 | 325 | 80 85 % |
| 03h | 316 | 274 | 86 71 % |
| 04h | 414 | 366 | 88 41 % |
| 05h | 499 | 357 | 71 54 % |
| 06h | 722 | 328 | 45 43 % |
| 07h | 1 603 | 368 | 22 96 % |
| 08h | 13 227 | 341 | 2 58 % |
| 09h | 19 861 | 371 | 1 87 % |
| 10h | 20 998 | 324 | 1 54 % |
| 11h | 22 379 | 339 | 1 51 % |
| 12h | 21 849 | 346 | 1 58 % |
| 13h | 20 601 | 353 | 1 71 % |
| 14h | 19 529 | 340 | 1 74 % |
| 15h | 20 703 | 345 | 1 67 % |
| 16h | 20 764 | 350 | 1 69 % |
| 17h | 26 751 | 343 | 1 28 % |
| 18h | 30 081 | 342 | 1 14 % |
| 19h | 25 526 | 339 | 1 33 % |
| 20h | 11 706 | 346 | 2 96 % |
| 21h | 9 251 | 349 | 3 77 % |
| 22h | 6 801 | 322 | 4 73 % |
| 23h | 3 647 | 300 | 8 23 % |
| **Total** | **299 983** | **8 197** | **2,73 %** |


**Pourquoi le taux de 88,41 % à 4h n'est pas une conclusion générale :** à 4h, il y a seulement **414 transactions** dont **366 fraudes**. Le taux est très élevé parce que le dénominateur est petit et parce que l'échantillon a été enrichi en fraudes. Les heures PaySim sont simulées : ne pas présenter ce résultat comme un risque réel à 4h au Togo ou ailleurs.

## 9. Contrôles qualité et limites

1. Concordance des KPI et du tableau horaire : **299 983** et **8 197**.
2. Les deux ratios sont calculés avec les mesures, et non avec des valeurs arrondies de cartes : d'où **18,80 %** et non **18,81 %**.
3. Le taux de fraude de **2,73 %** décrit **l'échantillon DWH**, non la prévalence de fraude dans le dataset brut ou le monde réel.
4. Le code ETL conserve toutes les fraudes initialement, puis exclut les transactions de montant nul ou négatif : la mention « 100 % des fraudes conservées » doit être nuancée.
5. Le calcul « montant des fraudes » est descriptif et ne mesure ni les pertes recouvrables ni les fraudes détectées par un algorithme.
6. Le champ `is_flagged_fraud` existe dans la base mais n'a pas encore fait l'objet d'une visualisation dédiée vérifiée dans le rapport.
7. Le format `8,197K` de la carte « Nombre de fraudes » reste à ajuster à **8 197** si souhaité ; cela ne change pas le calcul.

## 10. Étapes de réalisation — journal de bord

1. Connexion réussie à PostgreSQL Render.
2. Import des cinq tables.
3. Contrôle du schéma en étoile et des quatre relations.
4. Mesure `Total Transactions`.
5. Mesures `Nombre de fraudes` et `Taux de fraude`.
6. Mesure `Montant total`.
7. Visualisation des transactions par type.
8. Visualisation des fraudes par type.
9. Visualisation des taux par type.
10. Visualisation des transactions par heure.
11. Visualisation du nombre de fraudes par heure.
12. Visualisation du taux de fraude par heure.
13. Tableau de validation horaire.
14. Finalisation de la page 1.
15. Création de la page 2.
16. Mise en forme et conclusions de la page 2.
17. Mesure `Montant des fraudes` : **12,06 Md**.
18. Mesure `Part financière des fraudes` : **18,80 %**.
19. Sauvegarde du fichier PBIX.
20. Relecture visuelle et corrections mineures identifiées.


## 11. Livrables et reproductibilité

- `PaySim_Analyse_Fraude_LBS.pbix` : rapport Power BI sauvegardé localement, **non inclus dans le ZIP examiné**.
- Le présent README : documentation personnelle.
- Dépendance : accès autorisé à la base PostgreSQL Render ; si elle expire, le Data Engineer doit recréer le DWH à l'aide des scripts du dépôt.

**Sources internes :** code et documentation du ZIP `projet-paysim-main(1).zip` ; valeurs et visuels vérifiés lors des séances Power BI.


## Télécharger le tableau de bord Power BI

Le tableau de bord a été développé avec Power BI Desktop et contient deux pages :

- Vue d'ensemble des transactions et des fraudes
- Analyse détaillée des fraudes

**[Télécharger le fichier Power BI (.pbix)](https://github.com/Dominique12345678/projet-paysim/releases/download/data-analyst-v1.0/PaySim_Analyse_Fraude_LBS.pbix)**

> Remarque : les données proviennent d'un échantillon synthétique PaySim enrichi en fraudes.

