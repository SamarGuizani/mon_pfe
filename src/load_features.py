"""
Charge la table features_msisdn depuis PostgreSQL dans pandas.
Applique le split train/test et sauvegarde en CSV pour reutilisation.
"""
import pandas as pd
from sqlalchemy import text
from sklearn.model_selection import train_test_split
from db_connection import get_engine

print("[1/4] Connexion a PostgreSQL...")
engine = get_engine()

with engine.connect() as conn:
    # Verifier que la table features_msisdn existe
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'features_msisdn'
        )
    """))
    table_exists = result.fetchone()[0]

    if not table_exists:
        print("ERREUR : La table 'features_msisdn' n'existe pas.")
        print("Execute d'abord feature_engineering.sql dans pgAdmin ou psql.")
        exit(1)

    # Charger les features
    print("[2/4] Chargement des features depuis PostgreSQL...")
    df = pd.DataFrame(
        conn.execute(text("SELECT * FROM features_msisdn")).fetchall(),
        columns=conn.execute(text("SELECT * FROM features_msisdn LIMIT 0")).keys()
    )

print(f"      {len(df):,} msisdn charges avec {len(df.columns)} colonnes")
print(f"      Colonnes : {list(df.columns)}")
print(f"      Memoire : {df.memory_usage(deep=True).sum() / 1024**2:.1f} Mo")
print()

# Remplacer les valeurs nulles par 0 (important pour le ML)
df = df.fillna(0)

# Statistiques rapides
print("[3/4] Statistiques des features :")
print(df.describe().round(2).to_string())
print()

# Split train/test (70% train, 30% test)
print("[4/4] Split train/test (70/30)...")
train, test = train_test_split(df, test_size=0.3, random_state=42)

# Sauvegarder en CSV pour reutilisation (plus besoin de PostgreSQL apres)
train.to_csv("../data/train.csv", index=False)
test.to_csv("../data/test.csv", index=False)

print(f"      Train : {len(train):,} lignes -> data/train.csv")
print(f"      Test  : {len(test):,} lignes  -> data/test.csv")
print("\nTermine. Les fichiers CSV sont prets pour le Machine Learning.")
