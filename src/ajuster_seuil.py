"""
AJUSTEMENT DU SEUIL de decision pour le modele re-entraine (vrais labels).
Teste plusieurs seuils et trouve le meilleur compromis precision / rappel.
Ne modifie ni le modele ni les tables - met juste a jour data/metrics_real.json.
"""
import re
import json
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
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
print("  AJUSTEMENT DU SEUIL - modele re-entraine sur vrais labels")
print("=" * 64)

engine = get_engine()

# 1. Vrais fraudeurs
ent = pd.read_sql("SELECT msisdn FROM liste_entreprise", engine)
ent_keys = set(cle(v) for v in ent["msisdn"])
print(f"\n[1] Vrais fraudeurs entreprise : {len(ent_keys)}")

# 2. Features (re-chargement chunked - meme processus que le retrain)
print(f"[2] Chargement features_msisdn_fresh (par paquets)...")
chunks = []
for chunk in pd.read_sql("SELECT * FROM features_msisdn_fresh", engine, chunksize=500_000):
    chunks.append(chunk)
df = pd.concat(chunks, ignore_index=True)
del chunks
df = df.fillna(0)
for c in df.columns:
    if c != "msisdn":
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
df["cle"] = df["msisdn"].apply(cle)
df["label"] = df["cle"].isin(ent_keys).astype(int)
print(f"    {len(df):,} numeros, {int(df['label'].sum())} positifs")

# 3. MEME split que le retrain (random_state=42, stratify=y)
X = df[FEATURES]
y = df["label"]
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y
)
print(f"    Test : {len(X_test):,} ({int(y_test.sum())} vrais frauds caches)")

# 4. Predictions probabilistes
model = joblib.load("../models/xgboost_fraud_real.pkl")
y_proba = model.predict_proba(X_test)[:, 1]
auc = float(roc_auc_score(y_test, y_proba))
print(f"\n[3] AUC = {auc:.4f}")

# 5. Test de plusieurs seuils
print(f"\n[4] Comparaison des seuils :")
print(f"   {'Seuil':>7}  {'Detectes':>10}  {'VP':>5}  {'FP':>8}  {'FN':>5}  {'Precis':>8}  {'Rappel':>8}  {'F1':>8}")
for t in [0.30, 0.50, 0.70, 0.80, 0.90, 0.95, 0.99, 0.995, 0.999]:
    yp = (y_proba >= t).astype(int)
    vp = int(((yp == 1) & (y_test == 1)).sum())
    fp = int(((yp == 1) & (y_test == 0)).sum())
    fn = int(((yp == 0) & (y_test == 1)).sum())
    det = int(yp.sum())
    prec = vp / det if det else 0
    rec = vp / int(y_test.sum())
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
    print(f"   {t:>7.3f}  {det:>10}  {vp:>5}  {fp:>8}  {fn:>5}  {prec*100:>7.1f}%  {rec*100:>7.1f}%  {f1*100:>7.1f}%")

# 6. Recherche fine du seuil optimal (max F1)
print(f"\n[5] Recherche du seuil OPTIMAL (max F1) sur grille fine...")
thresholds = np.linspace(0.30, 0.9999, 500)
best = {"f1": 0, "t": 0.5, "prec": 0, "rec": 0, "det": 0, "vp": 0, "fp": 0, "fn": 0}
for t in thresholds:
    yp = (y_proba >= t).astype(int)
    det = int(yp.sum())
    if det == 0:
        continue
    vp = int(((yp == 1) & (y_test == 1)).sum())
    fp = int(((yp == 1) & (y_test == 0)).sum())
    fn = int(((yp == 0) & (y_test == 1)).sum())
    prec = vp / det
    rec = vp / int(y_test.sum())
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
    if f1 > best["f1"]:
        best = {"f1": f1, "t": float(t), "prec": prec, "rec": rec,
                "det": det, "vp": vp, "fp": fp, "fn": fn}

print(f"\n  SEUIL OPTIMAL : {best['t']:.4f}")
print(f"  Precision     : {best['prec']*100:.1f}%")
print(f"  Rappel        : {best['rec']*100:.1f}%")
print(f"  F1            : {best['f1']*100:.1f}%")
print(f"  Detectes      : {best['det']}  (VP={best['vp']}, FP={best['fp']}, FN={best['fn']})")

# 7. Mise a jour metrics_real.json
with open("../data/metrics_real.json", "r") as f:
    m = json.load(f)
m["best_threshold"] = round(best["t"], 4)
m["best_threshold_precision"] = round(best["prec"], 4)
m["best_threshold_recall"] = round(best["rec"], 4)
m["best_threshold_f1"] = round(best["f1"], 4)
m["best_threshold_detected"] = best["det"]
m["best_threshold_confusion"] = {
    "vrai_positif": best["vp"],
    "faux_positif": best["fp"],
    "faux_negatif": best["fn"],
}
with open("../data/metrics_real.json", "w") as f:
    json.dump(m, f, indent=2)
print(f"\n[6] data/metrics_real.json mis a jour avec le seuil optimal")
print("\nTermine !")
