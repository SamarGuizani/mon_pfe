"""
PROTOTYPE : Detection d'outliers (valeurs aberrantes) sur les features V2

3 methodes de detection :
  1. Z-Score    : un numero est outlier si sa valeur est a plus de 3 ecarts-types de la moyenne
  2. IQR        : un numero est outlier s'il depasse Q3 + 1.5 * (Q3 - Q1)
  3. Isolation Forest : algorithme ML qui isole les comportements rares

Le principe : un fraudeur SIM Box a un comportement TRES DIFFERENT d'un humain normal.
On cherche les numeros qui "sortent du lot" sur plusieurs indicateurs a la fois.
"""
import pandas as pd
import numpy as np
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from db_connection import get_engine
from sqlalchemy import text

print("=" * 60)
print("  PROTOTYPE - Detection d'outliers sur Features V2")
print("=" * 60)

# ============================================================
# ETAPE 1 : Charger les features V2 depuis PostgreSQL
# ============================================================
print("\n[1/6] Chargement des features V2...")
engine = get_engine()
with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM features_msisdn_v2"))
    df = pd.DataFrame(result.fetchall(), columns=result.keys())

df = df.fillna(0)
# Convertir les Decimal PostgreSQL en float pour numpy/sklearn
for col in df.columns:
    if col != "msisdn":
        df[col] = df[col].astype(float)
print(f"      {len(df):,} msisdn charges")
print(f"      Colonnes : {list(df.columns)}")

# Features numeriques pour la detection
features = [
    "nombre_appels", "appels_sortants", "appels_entrants",
    "duree_totale", "duree_sortants", "duree_entrants",
    "avg_duree_sortants", "avg_duree_entrants",
    "variance_sortants", "variance_entrants",
    "distinct_locations", "distinct_locations_sortants", "distinct_locations_entrants"
]
X = df[features]

# ============================================================
# METHODE 1 : Z-SCORE
# ============================================================
# Principe : si une valeur est a plus de 3 ecarts-types de la moyenne,
# c'est un outlier. Comme un eleve qui a 20/20 dans une classe
# ou la moyenne est 10 — il "sort du lot".
print("\n[2/6] Methode Z-Score (seuil = 3 ecarts-types)...")

scaler = StandardScaler()
X_scaled = pd.DataFrame(scaler.fit_transform(X), columns=features)

# Un numero est outlier si AU MOINS 3 features depassent le seuil de 3
z_outlier_count = (X_scaled.abs() > 3).sum(axis=1)
df["zscore_nb_features_outlier"] = z_outlier_count
df["zscore_outlier"] = (z_outlier_count >= 3).astype(int)

n_zscore = df["zscore_outlier"].sum()
print(f"      Outliers Z-Score : {n_zscore:,} ({100*n_zscore/len(df):.2f}%)")

# ============================================================
# METHODE 2 : IQR (Interquartile Range)
# ============================================================
# Principe : Q1 = 25%, Q3 = 75%, IQR = Q3 - Q1
# Outlier si valeur > Q3 + 1.5 * IQR  (methode des boites a moustaches)
print("\n[3/6] Methode IQR (boite a moustaches)...")

iqr_outlier_count = pd.Series(0, index=df.index)
for col in features:
    Q1 = X[col].quantile(0.25)
    Q3 = X[col].quantile(0.75)
    IQR = Q3 - Q1
    is_outlier = (X[col] > Q3 + 1.5 * IQR) | (X[col] < Q1 - 1.5 * IQR)
    iqr_outlier_count += is_outlier.astype(int)

df["iqr_nb_features_outlier"] = iqr_outlier_count
df["iqr_outlier"] = (iqr_outlier_count >= 3).astype(int)

n_iqr = df["iqr_outlier"].sum()
print(f"      Outliers IQR : {n_iqr:,} ({100*n_iqr/len(df):.2f}%)")

# ============================================================
# METHODE 3 : ISOLATION FOREST
# ============================================================
# Principe : l'algorithme essaie d'isoler chaque point.
# Les outliers sont FACILES a isoler (comportement unique).
# Les normaux sont DIFFICILES a isoler (comportement commun).
print("\n[4/6] Methode Isolation Forest (contamination=5%)...")

iso = IsolationForest(
    contamination=0.05,
    n_estimators=200,
    random_state=42,
    n_jobs=-1
)
iso.fit(X_scaled)

df["iforest_score"] = iso.decision_function(X_scaled)
df["iforest_outlier"] = (iso.predict(X_scaled) == -1).astype(int)

n_iforest = df["iforest_outlier"].sum()
print(f"      Outliers Isolation Forest : {n_iforest:,} ({100*n_iforest/len(df):.2f}%)")

# ============================================================
# ETAPE 5 : CONSENSUS (vote majoritaire)
# ============================================================
# Un numero est VRAIMENT suspect si au moins 2 methodes sur 3 le flaggent
print("\n[5/6] Consensus (au moins 2 methodes sur 3)...")

df["vote"] = df["zscore_outlier"] + df["iqr_outlier"] + df["iforest_outlier"]
df["suspect_final"] = (df["vote"] >= 2).astype(int)

n_final = df["suspect_final"].sum()
print(f"      Suspects finaux : {n_final:,} ({100*n_final/len(df):.2f}%)")

# Comparaison des 3 methodes
print(f"\n      === COMPARAISON ===")
print(f"      Z-Score          : {n_zscore:,}")
print(f"      IQR              : {n_iqr:,}")
print(f"      Isolation Forest : {n_iforest:,}")
print(f"      Consensus (>=2)  : {n_final:,}")

# ============================================================
# ETAPE 6 : TOP SUSPECTS + GRAPHIQUES
# ============================================================
print(f"\n[6/6] Top 20 suspects et graphiques...")

top20 = df.nsmallest(20, "iforest_score")[[
    "msisdn", "appels_sortants", "appels_entrants",
    "avg_duree_sortants", "variance_sortants",
    "distinct_locations", "vote", "iforest_score"
]]
print("\n      === TOP 20 NUMEROS LES PLUS SUSPECTS ===")
print(top20.to_string(index=False))

# --- Graphique 1 : Heatmap des correlations entre features ---
fig, ax = plt.subplots(figsize=(12, 10))
corr = X.corr()
sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0, ax=ax,
            xticklabels=[f.replace("_", "\n") for f in features],
            yticklabels=[f.replace("_", "\n") for f in features])
ax.set_title("Correlation entre les features V2", fontsize=14)
plt.tight_layout()
plt.savefig("../data/correlation_features_v2.png", dpi=150)
plt.close()
print("\n      -> data/correlation_features_v2.png")

# --- Graphique 2 : Distribution des votes ---
fig, ax = plt.subplots(figsize=(8, 5))
df["vote"].value_counts().sort_index().plot(kind="bar", color="steelblue", ax=ax)
ax.set_xlabel("Nombre de methodes qui flaggent le numero", fontsize=12)
ax.set_ylabel("Nombre de msisdn", fontsize=12)
ax.set_title("Distribution des votes (0=normal, 3=tres suspect)", fontsize=14)
plt.tight_layout()
plt.savefig("../data/outlier_votes.png", dpi=150)
plt.close()
print("      -> data/outlier_votes.png")

# --- Graphique 3 : Sortants vs Entrants (suspects en rouge) ---
fig, ax = plt.subplots(figsize=(10, 7))
sample_normal = df[df["suspect_final"] == 0].sample(min(5000, len(df)), random_state=42)
sample_suspect = df[df["suspect_final"] == 1].sample(min(2000, n_final), random_state=42)
ax.scatter(sample_normal["appels_sortants"], sample_normal["appels_entrants"],
           alpha=0.3, s=5, color="blue", label="Normal")
ax.scatter(sample_suspect["appels_sortants"], sample_suspect["appels_entrants"],
           alpha=0.5, s=10, color="red", label="Suspect")
ax.set_xlabel("Appels sortants", fontsize=12)
ax.set_ylabel("Appels entrants", fontsize=12)
ax.set_title("Appels sortants vs entrants (suspects en rouge)", fontsize=14)
ax.legend()
plt.tight_layout()
plt.savefig("../data/sortants_vs_entrants.png", dpi=150)
plt.close()
print("      -> data/sortants_vs_entrants.png")

# --- Graphique 4 : Variance sortants vs mobilite ---
fig, ax = plt.subplots(figsize=(10, 7))
ax.scatter(sample_normal["variance_sortants"], sample_normal["distinct_locations"],
           alpha=0.3, s=5, color="blue", label="Normal")
ax.scatter(sample_suspect["variance_sortants"], sample_suspect["distinct_locations"],
           alpha=0.5, s=10, color="red", label="Suspect")
ax.set_xlabel("Variance sortants (diversite des appeles)", fontsize=12)
ax.set_ylabel("Locations distinctes (mobilite)", fontsize=12)
ax.set_title("Variance sortants vs Mobilite (suspects en rouge)", fontsize=14)
ax.legend()
plt.tight_layout()
plt.savefig("../data/variance_vs_mobilite.png", dpi=150)
plt.close()
print("      -> data/variance_vs_mobilite.png")

# Sauvegarder
joblib.dump(iso, "../models/isolation_forest_v2.pkl")
joblib.dump(scaler, "../models/scaler_v2.pkl")
df.to_csv("../data/resultats_outliers_v2.csv", index=False)

print(f"\n      Modele   : models/isolation_forest_v2.pkl")
print(f"      Resultats : data/resultats_outliers_v2.csv")
print(f"\nTermine.")
