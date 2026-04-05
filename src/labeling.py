"""
Creation des pseudo-labels pour le Machine Learning.
On utilise des regles metier pour etiqueter les msisdn comme "fraude" ou "normal".

IMPORTANT : Ce sont des pseudo-labels, pas la verite absolue.
Le modele ML apprend a reproduire ces regles de maniere plus souple.
"""
import pandas as pd

print("[1/3] Chargement des donnees d'entrainement...")
train = pd.read_csv("../data/train.csv")
test = pd.read_csv("../data/test.csv")

print(f"      Train : {len(train):,} lignes")
print(f"      Test  : {len(test):,} lignes")

# ============================================================
# REGLES DE LABELING (basees sur le comportement SIM Box connu)
# ============================================================
# Un msisdn est considere "fraude" si AU MOINS 2 de ces conditions sont vraies :
#   1. Plus de 50 appels
#   2. Ratio d'appels courts > 60%
#   3. Peu de cellules uniques (<=3) -> fixe geographiquement
#   4. Plusieurs IMEI utilises (>=2)
#   5. Plus de 20 appels par jour


def labeler(df):
    """Applique les regles de labeling et retourne le DataFrame avec la colonne label_fraude"""
    conditions = pd.DataFrame()
    conditions["regle_volume"] = df["nombre_appels"] > 50
    conditions["regle_courts"] = df["ratio_appels_courts"] > 60
    conditions["regle_geo"] = df["nb_cellules_uniques"] <= 3
    conditions["regle_imei"] = df["nb_imei_utilises"] >= 2
    conditions["regle_intensite"] = df["appels_par_jour"] > 20

    # Fraude = au moins 2 regles validees
    nb_regles = conditions.sum(axis=1)
    df["label_fraude"] = (nb_regles >= 2).astype(int)

    return df


print("\n[2/3] Application des regles de labeling...")
train = labeler(train)
test = labeler(test)

# Statistiques
n_fraude_train = train["label_fraude"].sum()
n_normal_train = len(train) - n_fraude_train
n_fraude_test = test["label_fraude"].sum()
n_normal_test = len(test) - n_fraude_test

print(f"\n      === TRAIN ===")
print(f"      Normal : {n_normal_train:,} ({100*n_normal_train/len(train):.1f}%)")
print(f"      Fraude : {n_fraude_train:,} ({100*n_fraude_train/len(train):.1f}%)")
print(f"\n      === TEST ===")
print(f"      Normal : {n_normal_test:,} ({100*n_normal_test/len(test):.1f}%)")
print(f"      Fraude : {n_fraude_test:,} ({100*n_fraude_test/len(test):.1f}%)")

# Sauvegarder
print("\n[3/3] Sauvegarde...")
train.to_csv("../data/train_labeled.csv", index=False)
test.to_csv("../data/test_labeled.csv", index=False)

print("      data/train_labeled.csv et data/test_labeled.csv crees.")
print("\nTermine. Les donnees sont pretes pour l'entrainement ML.")
