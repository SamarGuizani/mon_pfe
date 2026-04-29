"""
XGBoost V3 - Re-entrainement avec la nouvelle liste noire (152 suspects)
Les labels viennent de liste_noire_fraude (filtree avec cell 412-54312)
"""
import pandas as pd
import numpy as np
import joblib
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sqlalchemy import text
from db_connection import get_engine

print("=" * 60)
print("  XGBOOST V3 - Avec nouvelle liste noire (cell 412-54312)")
print("=" * 60)

# 1. Charger les features V2
print("\n[1/6] Chargement des features V2...")
engine = get_engine()
df = pd.read_sql("SELECT * FROM features_msisdn_v2", engine)
df = df.fillna(0)

for col in df.columns:
    if col != "msisdn":
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

print(f"      {len(df):,} msisdn charges")

# 2. Charger la nouvelle liste noire (152 suspects)
print("\n[2/6] Chargement liste_noire_fraude (regles strictes)...")
liste_noire = pd.read_sql("SELECT msisdn FROM liste_noire_fraude", engine)
fraudes_set = set(liste_noire["msisdn"].astype(str))
print(f"      {len(fraudes_set):,} fraudes confirmees")

# 3. Creer les labels
print("\n[3/6] Creation des labels...")
df["msisdn_str"] = df["msisdn"].astype(str)
df["label_fraude"] = df["msisdn_str"].isin(fraudes_set).astype(int)

nb_fraude = df["label_fraude"].sum()
nb_normal = (df["label_fraude"] == 0).sum()
print(f"      Fraudes : {nb_fraude:,} ({100*nb_fraude/len(df):.4f}%)")
print(f"      Normaux : {nb_normal:,} ({100*nb_normal/len(df):.4f}%)")

# 4. Split 70/30 stratifie
print("\n[4/6] Split train/test (70/30 stratifie)...")
features = [
    "appels_sortants", "appels_entrants",
    "duree_sortants", "duree_entrants",
    "avg_duree_sortants", "avg_duree_entrants",
    "variance_sortants", "variance_entrants",
    "location_count", "location_count_sortants", "location_count_entrants",
    "active_hours", "distinct_imei",
    "unique_called", "unique_calling", "nb_jours_actifs"
]

X = df[features]
y = df["label_fraude"]

X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
    X, y, df.index, test_size=0.3, random_state=42, stratify=y
)
print(f"      Train : {len(X_train):,} ({y_train.sum()} fraudes)")
print(f"      Test  : {len(X_test):,} ({y_test.sum()} fraudes)")

# 5. Entrainer XGBoost
print("\n[5/6] Entrainement XGBoost...")
ratio = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
print(f"      Ratio desequilibre : {ratio:.0f}:1 (normal:fraude)")

model = xgb.XGBClassifier(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.1,
    scale_pos_weight=ratio,
    random_state=42,
    eval_metric="logloss",
    n_jobs=-1
)
model.fit(X_train, y_train)
print("      Modele entraine.")

# 6. Evaluation
print("\n[6/6] Evaluation sur le test set...")
y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

print("\n--- Classification Report ---")
print(classification_report(y_test, y_pred, target_names=["Normal", "Fraude"]))

cm = confusion_matrix(y_test, y_pred)
print("--- Matrice de Confusion ---")
print(f"      Vrais Negatifs  : {cm[0][0]:,}")
print(f"      Faux Positifs   : {cm[0][1]:,}")
print(f"      Faux Negatifs   : {cm[1][0]:,}")
print(f"      Vrais Positifs  : {cm[1][1]:,}")

auc = roc_auc_score(y_test, y_proba)
print(f"\n      ROC-AUC : {auc:.4f}")

# Creer liste_noire_train et liste_noire_test
print("\n[Bonus] Creation liste_noire_train et liste_noire_test...")

train_frauds = df.loc[idx_train[y_train == 1]].copy()
test_df = df.loc[idx_test].copy()
test_df["xgb_pred"] = y_pred
test_df["xgb_proba"] = y_proba
test_frauds = test_df[test_df["xgb_pred"] == 1].copy()

print(f"      Suspects TRAIN (vrais labels) : {len(train_frauds)}")
print(f"      Suspects TEST detectes par XGBoost : {len(test_frauds)}")

with engine.begin() as conn:
    conn.execute(text("DROP TABLE IF EXISTS liste_noire_train CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS liste_noire_test CASCADE"))

cols_to_save = ["msisdn"] + features
train_frauds[cols_to_save].to_sql("liste_noire_train", engine, if_exists="replace", index=False)
test_save = test_frauds[cols_to_save + ["xgb_proba"]].copy()
test_save.to_sql("liste_noire_test", engine, if_exists="replace", index=False)

# Sauvegarder le modele
joblib.dump(model, "../models/xgboost_fraud_v3.pkl")
print(f"\n      Modele : models/xgboost_fraud_v3.pkl")
print(f"      Tables : liste_noire_train, liste_noire_test")

# Sauvegarder les metriques
report = classification_report(y_test, y_pred, output_dict=True, target_names=["Normal", "Fraude"])
metrics = {
    "train_size": int(len(X_train)),
    "train_fraudes": int((y_train == 1).sum()),
    "test_size": int(len(X_test)),
    "test_fraudes": int((y_test == 1).sum()),
    "fraudes_detectees_test": int(y_pred.sum()),
    "precision": float(report["Fraude"]["precision"]),
    "recall": float(report["Fraude"]["recall"]),
    "f1": float(report["Fraude"]["f1-score"]),
    "auc": float(auc),
    "confusion_matrix": {
        "vrai_negatif": int(cm[0][0]),
        "faux_positif": int(cm[0][1]),
        "faux_negatif": int(cm[1][0]),
        "vrai_positif": int(cm[1][1])
    }
}
import json
with open("../data/metrics_v3.json", "w") as f:
    json.dump(metrics, f, indent=2)
print(f"      Metriques : data/metrics_v3.json")

print("\nTermine !")
