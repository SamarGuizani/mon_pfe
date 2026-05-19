"""
TEST INDEPENDANT - DONNEES FRESH (cdr_new, mai 2026)
=====================================================
Ce script NE RE-ENTRAINE RIEN.
Il charge les modeles XGBoost DEJA entraines et les teste sur des
donnees totalement nouvelles (table features_msisdn_fresh) que le
modele n'a JAMAIS vues pendant l'entrainement.

Reference de comparaison : la regle metier SIM Box de l'entreprise
appliquee aux donnees fresh (la meme regle que l'entrainement V2).

Sorties :
  - data/metrics_fresh.json   (precision / rappel / F1 / AUC par modele)
  - table liste_noire_fresh   (les suspects detectes sur les donnees neuves)
"""
import os
import json
import pandas as pd
import joblib
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sqlalchemy import text
from db_connection import get_engine

FEATURES = [
    "appels_sortants", "appels_entrants",
    "duree_sortants", "duree_entrants",
    "avg_duree_sortants", "avg_duree_entrants",
    "variance_sortants", "variance_entrants",
    "location_count", "location_count_sortants", "location_count_entrants",
    "active_hours", "distinct_imei",
    "unique_called", "unique_calling", "nb_jours_actifs",
]

print("=" * 60)
print("  TEST INDEPENDANT - DONNEES FRESH (jamais vues)")
print("=" * 60)

# 1. Charger les features fresh
print("\n[1/5] Chargement de features_msisdn_fresh...")
engine = get_engine()
df = pd.read_sql("SELECT * FROM features_msisdn_fresh", engine)
df = df.fillna(0)
for col in df.columns:
    if col != "msisdn":
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
print(f"      {len(df):,} numeros (msisdn) dans les donnees fresh")

# 2. Reference : regle metier SIM Box (identique a l'entrainement V2)
print("\n[2/5] Application de la regle metier SIM Box (reference)...")
df["label_regle"] = (
    (df["appels_sortants"] >= 15)
    & ((df["variance_sortants"] >= 85)
       | (df["distinct_imei"] >= 3)
       | (df["location_count"] <= 3))
).astype(int)
n_fraude_regle = int(df["label_regle"].sum())
print(f"      Regle SIM Box : {n_fraude_regle:,} suspects sur {len(df):,} numeros")

X = df[FEATURES]
y = df["label_regle"]
resultats = {}

# 3. Tester chaque modele DEJA entraine
print("\n[3/5] Test des modeles deja entraines sur les donnees fresh...")
for nom, chemin in [("XGBoost V2", "../models/xgboost_fraud_v2.pkl"),
                    ("XGBoost V3", "../models/xgboost_fraud_v3.pkl")]:
    if not os.path.exists(chemin):
        print(f"      ({nom} introuvable, ignore)")
        continue

    model = joblib.load(chemin)
    y_pred = model.predict(X)
    y_proba = model.predict_proba(X)[:, 1]

    rep = classification_report(y, y_pred, target_names=["Normal", "Fraude"],
                                output_dict=True, zero_division=0)
    cm = confusion_matrix(y, y_pred, labels=[0, 1])
    try:
        auc = float(roc_auc_score(y, y_proba))
    except Exception:
        auc = 0.0

    print(f"\n   --- {nom} ---")
    print(classification_report(y, y_pred, target_names=["Normal", "Fraude"],
                                zero_division=0))
    print(f"      Suspects detectes par le modele : {int(y_pred.sum()):,}")
    print(f"      AUC : {auc:.4f}")

    resultats[nom] = {
        "modele": nom,
        "nb_numeros": int(len(df)),
        "suspects_regle": n_fraude_regle,
        "suspects_modele": int(y_pred.sum()),
        "precision": round(rep["Fraude"]["precision"], 4),
        "recall": round(rep["Fraude"]["recall"], 4),
        "f1": round(rep["Fraude"]["f1-score"], 4),
        "auc": round(auc, 4),
        "confusion_matrix": {
            "vrai_negatif": int(cm[0][0]),
            "faux_positif": int(cm[0][1]),
            "faux_negatif": int(cm[1][0]),
            "vrai_positif": int(cm[1][1]),
        },
    }

# 4. Sauvegarder les metriques
print("\n[4/5] Sauvegarde des metriques...")
with open("../data/metrics_fresh.json", "w") as f:
    json.dump(resultats, f, indent=2)
print("      data/metrics_fresh.json cree")

# 5. Creer la table liste_noire_fresh (suspects detectes par le modele V2)
print("\n[5/5] Creation de la table liste_noire_fresh (modele V2)...")
model = joblib.load("../models/xgboost_fraud_v2.pkl")
df["xgb_pred"] = model.predict(X)
df["xgb_proba"] = model.predict_proba(X)[:, 1]
suspects = df[df["xgb_pred"] == 1].copy()

cols = ["msisdn"] + FEATURES + ["xgb_proba"]
with engine.begin() as conn:
    conn.execute(text("DROP TABLE IF EXISTS liste_noire_fresh CASCADE"))
suspects[cols].to_sql("liste_noire_fresh", engine, if_exists="replace", index=False)
print(f"      {len(suspects):,} suspects -> table liste_noire_fresh")

print("\nTermine ! Test independant sur donnees fresh fini.")
