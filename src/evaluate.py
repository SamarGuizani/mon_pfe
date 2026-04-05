"""
Script d'evaluation : genere tous les graphiques pour le rapport PFE.
- Matrice de confusion
- Courbe ROC
- Feature importance
- Comparaison des modeles
- Distribution des scores d'anomalie
"""
import pandas as pd
import numpy as np
import joblib
import matplotlib
matplotlib.use("Agg")  # Pour sauvegarder sans afficher (compatible WSL)
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_curve, roc_auc_score, precision_recall_curve
)

print("=" * 60)
print("  EVALUATION - Generation des graphiques pour le PFE")
print("=" * 60)

# Charger les resultats
print("\n[1/6] Chargement des donnees et modeles...")
test_xgb = pd.read_csv("../data/test_with_xgb.csv")
model_xgb = joblib.load("../models/xgboost_fraud.pkl")

features = [
    "nombre_appels", "duree_totale_sec", "duree_moyenne",
    "ratio_appels_courts", "nb_destinataires_uniques",
    "nb_imei_utilises", "nb_cellules_uniques", "nb_lac_uniques",
    "nb_jours_actifs", "appels_par_jour", "heures_activite_totale",
    "ratio_appels_sortants"
]

y_test = test_xgb["label_fraude"]
y_pred = test_xgb["xgb_pred"]
y_proba = test_xgb["xgb_proba"]

# ============================================================
# 1. MATRICE DE CONFUSION
# ============================================================
print("[2/6] Matrice de confusion...")
cm = confusion_matrix(y_test, y_pred)
fig, ax = plt.subplots(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt=",d", cmap="Blues",
            xticklabels=["Normal", "Fraude"],
            yticklabels=["Normal", "Fraude"], ax=ax)
ax.set_xlabel("Prediction", fontsize=12)
ax.set_ylabel("Realite", fontsize=12)
ax.set_title("Matrice de Confusion - XGBoost", fontsize=14)
plt.tight_layout()
plt.savefig("../data/confusion_matrix.png", dpi=150)
plt.close()
print("      -> data/confusion_matrix.png")

# ============================================================
# 2. COURBE ROC
# ============================================================
print("[3/6] Courbe ROC...")
fpr, tpr, _ = roc_curve(y_test, y_proba)
auc = roc_auc_score(y_test, y_proba)

fig, ax = plt.subplots(figsize=(8, 6))
ax.plot(fpr, tpr, color="blue", lw=2, label=f"XGBoost (AUC = {auc:.4f})")
ax.plot([0, 1], [0, 1], color="gray", linestyle="--", label="Aleatoire (AUC = 0.5)")
ax.set_xlabel("Taux de Faux Positifs", fontsize=12)
ax.set_ylabel("Taux de Vrais Positifs", fontsize=12)
ax.set_title("Courbe ROC - Detection de Fraude SIM Box", fontsize=14)
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("../data/roc_curve.png", dpi=150)
plt.close()
print(f"      -> data/roc_curve.png (AUC = {auc:.4f})")

# ============================================================
# 3. COURBE PRECISION-RECALL
# ============================================================
print("[4/6] Courbe Precision-Recall...")
precision, recall, _ = precision_recall_curve(y_test, y_proba)

fig, ax = plt.subplots(figsize=(8, 6))
ax.plot(recall, precision, color="green", lw=2)
ax.set_xlabel("Recall (Fraudes attrapees)", fontsize=12)
ax.set_ylabel("Precision (Predictions correctes)", fontsize=12)
ax.set_title("Courbe Precision-Recall - XGBoost", fontsize=14)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("../data/precision_recall_curve.png", dpi=150)
plt.close()
print("      -> data/precision_recall_curve.png")

# ============================================================
# 4. FEATURE IMPORTANCE
# ============================================================
print("[5/6] Feature importance...")
importances = pd.Series(model_xgb.feature_importances_, index=features)
importances = importances.sort_values(ascending=True)

fig, ax = plt.subplots(figsize=(10, 7))
importances.plot(kind="barh", color="steelblue", ax=ax)
ax.set_xlabel("Importance", fontsize=12)
ax.set_title("Importance des Features - XGBoost", fontsize=14)
plt.tight_layout()
plt.savefig("../data/feature_importance.png", dpi=150)
plt.close()
print("      -> data/feature_importance.png")

# ============================================================
# 5. DISTRIBUTION DES SCORES
# ============================================================
print("[6/6] Distribution des scores...")
fig, ax = plt.subplots(figsize=(10, 6))
ax.hist(y_proba[y_test == 0], bins=50, alpha=0.6, label="Normal", color="blue")
ax.hist(y_proba[y_test == 1], bins=50, alpha=0.6, label="Fraude", color="red")
ax.set_xlabel("Score de probabilite (fraude)", fontsize=12)
ax.set_ylabel("Nombre de msisdn", fontsize=12)
ax.set_title("Distribution des scores - Normal vs Fraude", fontsize=14)
ax.legend(fontsize=11)
plt.tight_layout()
plt.savefig("../data/score_distribution.png", dpi=150)
plt.close()
print("      -> data/score_distribution.png")

# ============================================================
# RESUME FINAL
# ============================================================
print("\n" + "=" * 60)
print("  RESUME DES RESULTATS")
print("=" * 60)
print(classification_report(y_test, y_pred, target_names=["Normal", "Fraude"]))
print(f"  ROC-AUC : {auc:.4f}")
print(f"\n  Graphiques generes dans data/ :")
print(f"    - confusion_matrix.png")
print(f"    - roc_curve.png")
print(f"    - precision_recall_curve.png")
print(f"    - feature_importance.png")
print(f"    - score_distribution.png")
print(f"\nTermine. Ces graphiques sont prets pour le rapport PFE.")
