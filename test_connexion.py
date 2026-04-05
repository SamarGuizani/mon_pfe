from sqlalchemy import create_engine, text

# Ta clé pour ouvrir la base de données
# Format : postgresql://utilisateur:mot_de_passe@adresse:port/nom_base
conn_string = 'postgresql://postgres:samar123@127.0.0.1:5432/postgres'

engine = create_engine(conn_string)

try:
    # On essaie de demander à la base de nous donner la version du serveur
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        version = result.fetchone()[0]
        print("✅ CONNEXION RÉUSSIE !")
        print(f"PostgreSQL est prêt : {version[:30]}...")
except Exception as e:
    print(f"❌ Erreur : {e}")
