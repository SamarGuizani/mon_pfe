"""
RE-ENTRAINEMENT XGBoost sur les VRAIS numeros confirmes par l'entreprise.

Methode honnete :
  - Labels = les 207 numeros de la table liste_entreprise (vraies fraudes confirmees)
  - Split STRATIFIE : les 207 sont separes ~70/30 (train ~145, test ~62)
  - Le modele apprend sur le train, on l'evalue sur le test (vraies fraudes JAMAIS vues)
  - => evaluation honnete, pas d'overfitting cache
Sortie : models/xgboost_fraud_real.pkl + data/metrics_real.json + table liste_noire_real
"""
import re
import json
import pandas as pd
import joblib
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, precision_score, recall_score, f1_score
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


def cle(x):
    s = str(x).strip()
    if s.endswith(".0"):
        s = s[:-2]
    d = re.sub(r"\D", "", s)
    return d[-8:] if len(d) >= 8 else d


print("=" * 64)
print("  RE-ENTRAINEMENT sur les VRAIS numeros confirmes (entreprise)")
print("=" * 64)

engine = get_engine()

# 1. Liste entreprise (vrais frauds)
ent = pd.read_sql("SELECT msisdn FROM liste_entreprise", engine)
ent_keys = set(cle(v) for v in ent["msisdn"])
print(f"\n[1] Vrais fraudeurs entreprise : {len(ent_keys)} numeros distincts")

# 2. Features fresh (par paquets pour eviter une charge memoire serveur)
print(f"\n[2] Chargement de features_msisdn_fresh (par paquets de 500k)...")
chunks = []
total_lu = 0
for chunk in pd.read_sql("SELECT * FROM features_msisdn_fresh", engine, chunksize=500_000):
    chunks.append(chunk)
    total_lu += len(chunk)
    print(f"    ... {total_lu:,} lignes lues")
df = pd.concat(chunks, ignore_index=True)
del chunks
df = df.fillna(0)
for c in df.columns:
    if c != "msisdn":
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
df["cle"] = df["msisdn"].apply(cle)
df["label_reel"] = df["cle"].isin(ent_keys).astype(int)

n_pos = int(df["label_reel"].sum())
n_neg = len(df) - n_pos
print(f"\n    Total numeros          : {len(df):,}")
print(f"    Positifs (vraies fraudes confirmees presentes) : {n_pos}")
print(f"    Negatifs (le reste)    : {n_neg:,}")

if n_pos < 10:
    raise SystemExit("Trop peu de positifs trouves dans features_msisdn_fresh. Verifier le format des numeros.")

# 3. Split stratifie (les 207 sont splittes ~70/30, les negatifs aussi)
print(f"\n[3] Split train/test 70/30 (stratifie sur le label)...")
X = df[FEATURES]
y = df["label_reel"]
X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
    X, y, df.index, test_size=0.3, random_state=42, stratify=y
)
print(f"    Train : {len(X_train):,} ({int(y_train.sum())} vraies fraudes)")
print(f"    Test  : {len(X_test):,} ({int(y_test.sum())} vraies fraudes - JAMAIS vues)")

# 4. Entrainement
print(f"\n[4] Entrainement XGBoost...")
ratio = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
print(f"    Ratio desequilibre : {ratio:.0f}:1 (normal:fraude)")
model = xgb.XGBClassifier(
    n_estimators=200, max_depth=6, learning_rate=0.1,
    scale_pos_weight=ratio, random_state=42,
    eval_metric="logloss", n_jobs=-1,
)
model.fit(X_train, y_train)
print("    Modele entraine.")

# 5. Evaluation HONNETE
print(f"\n[5] Evaluation sur le test set (vraies fraudes JAMAIS vues)")
y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

print("\n" + classification_report(y_test, y_pred, target_names=["Normal", "Fraude"], zero_division=0))
cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
print(f"  Matrice de confusion :")
print(f"    Vrai Negatif (VN) : {cm[0][0]:,}")
print(f"    Faux Positif (FP) : {cm[0][1]}")
print(f"    Faux Negatif (FN) : {cm[1][0]}")
print(f"    Vrai Positif (VP) : {cm[1][1]}")
try:
    auc = float(roc_auc_score(y_test, y_proba))
except Exception:
    auc = 0.0
prec = float(precision_score(y_test, y_pred, zero_division=0))
rec = float(recall_score(y_test, y_pred, zero_division=0))
f1 = float(f1_score(y_test, y_pred, zero_division=0))
print(f"  Precision : {prec*100:.1f}%")
print(f"  Rappel    : {rec*100:.1f}%")
print(f"  F1-Score  : {f1*100:.1f}%")
print(f"  AUC       : {auc:.4f}")

# 6. Sauvegarde modele + metriques
joblib.dump(model, "../models/xgboost_fraud_real.pkl")
metrics = {
    "train_size": int(len(X_train)),
    "train_fraudes": int(y_train.sum()),
    "test_size": int(len(X_test)),
    "test_fraudes": int(y_test.sum()),
    "fraudes_detectees_test": int(y_pred.sum()),
    "precision": round(prec, 4),
    "recall": round(rec, 4),
    "f1": round(f1, 4),
    "auc": round(auc, 4),
    "confusion_matrix": {
        "vrai_negatif": int(cm[0][0]),
        "faux_positif": int(cm[0][1]),
        "faux_negatif": int(cm[1][0]),
        "vrai_positif": int(cm[1][1]),
    },
}
with open("../data/metrics_real.json", "w") as f:
    json.dump(metrics, f, indent=2)
print(f"\n[6] Modele     : models/xgboost_fraud_real.pkl")
print(f"    Metriques  : data/metrics_real.json")

# 7. Table liste_noire_real (suspects detectes sur le test)
df_test = df.loc[idx_test].copy()
df_test["pred"] = y_pred
df_test["proba"] = y_proba
suspects = df_test[df_test["pred"] == 1].copy()
cols = ["msisdn"] + FEATURES + ["proba"]
with engine.begin() as conn:
    conn.execute(text("DROP TABLE IF EXISTS liste_noire_real CASCADE"))
suspects[cols].to_sql("liste_noire_real", engine, if_exists="replace", index=False)
print(f"[7] Table 'liste_noire_real' creee ({len(suspects)} suspects detectes sur le test)")

print("\nTermine !")
