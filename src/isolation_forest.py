"""
Approche A : Detection d'anomalies SANS labels (Unsupervised)
Isolation Forest isole les msisdn "bizarres" automatiquement.

Principe : les fraudeurs ont un comportement DIFFERENT de la majorite.
L'algorithme n'a pas besoin qu'on lui dise qui est fraudeur.
"""
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

print("=" * 60)
print("  ISOLATION FOREST - Detection d'anomalies (Unsupervised)")
print("=" * 60)

# Charger les donnees
print("\n[1/4] Chargement des donnees...")
train = pd.read_csv("../data/train_labeled.csv")
test = pd.read_csv("../data/test_labeled.csv")

# Features a utiliser (toutes sauf msisdn et label)
features = [
    "nombre_appels", "duree_totale_sec", "duree_moyenne",
    "ratio_appels_courts", "nb_destinataires_uniques",
    "nb_imei_utilises", "nb_cellules_uniques", "nb_lac_uniques",
    "nb_jours_actifs", "appels_par_jour", "heures_activite_totale",
    "ratio_appels_sortants"
]

X_train = train[features].fillna(0)
X_test = test[features].fillna(0)

# Normaliser les features (important pour Isolation Forest)
print("[2/4] Normalisation des features...")
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Entrainer Isolation Forest
# contamination = proportion estimee de fraudeurs (5%)
print("[3/4] Entrainement Isolation Forest (contamination=5%)...")
model = IsolationForest(
    contamination=0.05,
    n_estimators=200,
    max_samples="auto",
    random_state=42,
    n_jobs=-1
)
model.fit(X_train_scaled)

# Predictions : -1 = anomalie (fraude), 1 = normal
train_pred = model.predict(X_train_scaled)
test_pred = model.predict(X_test_scaled)

# Scores d'anomalie (plus c'est negatif, plus c'est suspect)
train_scores = model.decision_function(X_train_scaled)
test_scores = model.decision_function(X_test_scaled)

# Ajouter les resultats
train["anomaly_pred"] = (train_pred == -1).astype(int)
train["anomaly_score"] = train_scores
test["anomaly_pred"] = (test_pred == -1).astype(int)
test["anomaly_score"] = test_scores

# Resultats
n_anomalies_train = (train_pred == -1).sum()
n_anomalies_test = (test_pred == -1).sum()

print(f"\n[4/4] Resultats :")
print(f"\n      === TRAIN ===")
print(f"      Anomalies detectees : {n_anomalies_train:,} / {len(train):,} ({100*n_anomalies_train/len(train):.1f}%)")
print(f"\n      === TEST ===")
print(f"      Anomalies detectees : {n_anomalies_test:,} / {len(test):,} ({100*n_anomalies_test/len(test):.1f}%)")

# Comparer avec les pseudo-labels
if "label_fraude" in test.columns:
    overlap = ((test["anomaly_pred"] == 1) & (test["label_fraude"] == 1)).sum()
    total_labels = test["label_fraude"].sum()
    total_anomalies = test["anomaly_pred"].sum()
    print(f"\n      === COMPARAISON avec pseudo-labels ===")
    print(f"      Pseudo-labels fraude : {total_labels:,}")
    print(f"      Anomalies detectees  : {total_anomalies:,}")
    print(f"      Overlap              : {overlap:,}")

# Top 10 anomalies (les plus suspectes)
print(f"\n      === TOP 10 NUMEROS LES PLUS SUSPECTS ===")
top10 = test.nsmallest(10, "anomaly_score")[["msisdn", "nombre_appels", "duree_moyenne",
    "ratio_appels_courts", "nb_cellules_uniques", "anomaly_score"]]
print(top10.to_string(index=False))

# Sauvegarder le modele et les resultats
joblib.dump(model, "../models/isolation_forest.pkl")
joblib.dump(scaler, "../models/scaler.pkl")
test.to_csv("../data/test_with_anomalies.csv", index=False)

print(f"\n      Modele sauvegarde : models/isolation_forest.pkl")
print(f"      Resultats test   : data/test_with_anomalies.csv")
print("\nTermine.")
