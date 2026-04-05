"""
Approche B : Classification supervisee avec XGBoost
Utilise les pseudo-labels pour apprendre a distinguer fraude vs normal.

XGBoost = algorithme puissant base sur des arbres de decision.
Avantage : gere bien les donnees desequilibrees (peu de fraudes, beaucoup de normaux).
"""
import pandas as pd
import numpy as np
import joblib
import xgboost as xgb
from sklearn.model_selection import cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score

print("=" * 60)
print("  XGBOOST - Classification supervisee")
print("=" * 60)

# Charger les donnees labelisees
print("\n[1/5] Chargement des donnees...")
train = pd.read_csv("../data/train_labeled.csv")
test = pd.read_csv("../data/test_labeled.csv")

# Features (sans msisdn et sans label)
features = [
    "nombre_appels", "duree_totale_sec", "duree_moyenne",
    "ratio_appels_courts", "nb_destinataires_uniques",
    "nb_imei_utilises", "nb_cellules_uniques", "nb_lac_uniques",
    "nb_jours_actifs", "appels_par_jour", "heures_activite_totale",
    "ratio_appels_sortants"
]

X_train = train[features].fillna(0)
y_train = train["label_fraude"]
X_test = test[features].fillna(0)
y_test = test["label_fraude"]

print(f"      Train : {len(X_train):,} lignes ({y_train.sum():,} fraudes)")
print(f"      Test  : {len(X_test):,} lignes ({y_test.sum():,} fraudes)")

# Calculer le ratio de desequilibre
# scale_pos_weight = nb_normaux / nb_fraudes
# Ca dit a XGBoost : "les fraudes sont rares, fais plus attention a elles"
ratio = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
print(f"      Ratio desequilibre : {ratio:.1f}:1 (normal:fraude)")

# Entrainer XGBoost
print("\n[2/5] Entrainement XGBoost...")
model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    scale_pos_weight=ratio,
    random_state=42,
    eval_metric="logloss",
    n_jobs=-1
)
model.fit(X_train, y_train)

# Predictions
print("[3/5] Predictions sur le test set...")
y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

# Evaluation
print("\n[4/5] Evaluation :")
print("\n--- Classification Report ---")
print(classification_report(y_test, y_pred, target_names=["Normal", "Fraude"]))

print("--- Matrice de Confusion ---")
cm = confusion_matrix(y_test, y_pred)
print(f"      Vrais Negatifs  (Normal predit Normal)  : {cm[0][0]:,}")
print(f"      Faux Positifs   (Normal predit Fraude)   : {cm[0][1]:,}")
print(f"      Faux Negatifs   (Fraude predit Normal)   : {cm[1][0]:,}")
print(f"      Vrais Positifs  (Fraude predit Fraude)   : {cm[1][1]:,}")

auc = roc_auc_score(y_test, y_proba)
print(f"\n      ROC-AUC : {auc:.4f}")

# Cross-validation (5-fold)
print("\n[5/5] Cross-validation (5-fold)...")
cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring="f1")
print(f"      F1 moyen : {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

# Feature importance (quelles features comptent le plus)
print("\n--- Feature Importance ---")
importances = pd.Series(model.feature_importances_, index=features)
importances = importances.sort_values(ascending=False)
for feat, imp in importances.items():
    bar = "#" * int(imp * 50)
    print(f"      {feat:30s} {imp:.4f} {bar}")

# Sauvegarder
joblib.dump(model, "../models/xgboost_fraud.pkl")
test["xgb_pred"] = y_pred
test["xgb_proba"] = y_proba
test.to_csv("../data/test_with_xgb.csv", index=False)

print(f"\n      Modele sauvegarde   : models/xgboost_fraud.pkl")
print(f"      Resultats test      : data/test_with_xgb.csv")
print("\nTermine.")
