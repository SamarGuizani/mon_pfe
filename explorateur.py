import pandas as pd
from sqlalchemy import create_engine, text

engine = create_engine('postgresql://postgres:samar123@127.0.0.1:5432/postgres')

# On récupère un échantillon de données
with engine.connect() as conn:
    # Remplace 'ma_table_cdr' par le nom d'une table que tu as vue dans pgAdmin
    query = text("SELECT * FROM ma_table_cdr LIMIT 100")
    df = pd.read_sql(query, conn)

print("Colonnes disponibles :", df.columns)
print(df.head())
