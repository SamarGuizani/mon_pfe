"""
Migre un ECHANTILLON de la base locale (PostgreSQL Windows) vers Neon (cloud).

Strategie :
  - Tables petites  -> copie INTEGRALE  (users, listes noires, IMEI, verification)
  - Tables enormes  -> copie d'un ECHANTILLON
       * tous les MSISDN des listes noires (suspects)
       * + N MSISDN normaux aleatoires (pour pouvoir tester avec des "normaux")

Utilisation :
  cd /home/samar/stage/mon_pfe
  source venv/bin/activate
  python src/migrate_to_neon.py
"""
import os
import sys
import time
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(__file__))
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

from db_connection import trouver_ip_windows

NB_NORMAUX_V2 = 50_000
NB_NORMAUX_FRESH = 50_000

# ---------------- Connexions ----------------
NEON_URL = os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+psycopg://", 1)
print(f"[1/8] Connexion source (Windows) ...")
ip = trouver_ip_windows()
src = create_engine(f"postgresql+psycopg://postgres:samar123@{ip}:5432/postgres")

print(f"[2/8] Connexion destination (Neon) ...")
dst = create_engine(NEON_URL)

with dst.connect() as c:
    print("        OK ->", c.execute(text("SELECT version()")).fetchone()[0][:60])


def copier_table_complete(nom_table):
    """Copie ENTIEREMENT une table (DDL recree + donnees)."""
    print(f"  -> {nom_table}")
    with src.connect() as cs:
        # Recuperer DDL minimale via information_schema (recreation simple)
        cols = cs.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = :t
            ORDER BY ordinal_position
        """), {"t": nom_table}).fetchall()

        ddl_cols = ", ".join(f'"{c[0]}" {c[1]}' for c in cols)
        ddl = f'CREATE TABLE IF NOT EXISTS "{nom_table}" ({ddl_cols})'

        with dst.begin() as cd:
            cd.execute(text(f'DROP TABLE IF EXISTS "{nom_table}" CASCADE'))
            cd.execute(text(ddl))

        rows = cs.execute(text(f'SELECT * FROM "{nom_table}"')).fetchall()
        if not rows:
            print(f"        (vide)")
            return

        col_names = [c[0] for c in cols]
        placeholders = ", ".join(f":{c}" for c in col_names)
        insert_sql = text(f'INSERT INTO "{nom_table}" ({", ".join(f"""\"{c}\"""" for c in col_names)}) VALUES ({placeholders})')

        with dst.begin() as cd:
            batch = []
            for r in rows:
                batch.append({col_names[i]: r[i] for i in range(len(col_names))})
                if len(batch) >= 1000:
                    cd.execute(insert_sql, batch)
                    batch = []
            if batch:
                cd.execute(insert_sql, batch)
        print(f"        OK ({len(rows):,} lignes)")


def copier_features_echantillon(table_features, table_suspects, n_normaux):
    """Copie : tous les suspects + echantillon de normaux d'une table features."""
    print(f"  -> {table_features} (suspects + {n_normaux:,} normaux)")
    with src.connect() as cs:
        cols = cs.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = :t
            ORDER BY ordinal_position
        """), {"t": table_features}).fetchall()
        ddl_cols = ", ".join(f'"{c[0]}" {c[1]}' for c in cols)

        with dst.begin() as cd:
            cd.execute(text(f'DROP TABLE IF EXISTS "{table_features}" CASCADE'))
            cd.execute(text(f'CREATE TABLE "{table_features}" ({ddl_cols})'))

        # SELECT tous les suspects + N normaux aleatoires
        rows = cs.execute(text(f"""
            SELECT * FROM {table_features}
            WHERE msisdn IN (SELECT msisdn FROM {table_suspects})
            UNION ALL
            (SELECT * FROM {table_features}
             WHERE msisdn NOT IN (SELECT msisdn FROM {table_suspects})
             ORDER BY random()
             LIMIT {n_normaux})
        """)).fetchall()

        col_names = [c[0] for c in cols]
        placeholders = ", ".join(f":{c}" for c in col_names)
        insert_sql = text(f'INSERT INTO "{table_features}" ({", ".join(f"""\"{c}\"""" for c in col_names)}) VALUES ({placeholders})')

        with dst.begin() as cd:
            batch = []
            for r in rows:
                batch.append({col_names[i]: r[i] for i in range(len(col_names))})
                if len(batch) >= 1000:
                    cd.execute(insert_sql, batch)
                    batch = []
            if batch:
                cd.execute(insert_sql, batch)

        with dst.begin() as cd:
            cd.execute(text(f'CREATE INDEX IF NOT EXISTS idx_{table_features}_msisdn ON "{table_features}"(msisdn)'))
        print(f"        OK ({len(rows):,} lignes)")


# ---------------- MIGRATION ----------------
t0 = time.time()
print("\n[3/8] Tables d'authentification & verification ...")
for t in ["users", "login_history", "verification_fraude", "fraudes_confirmees_manuelle"]:
    try:
        copier_table_complete(t)
    except Exception as e:
        print(f"        SKIP {t} : {str(e)[:80]}")

print("\n[4/8] Listes noires (suspects) ...")
for t in ["liste_noire_fraude", "liste_noire_fresh", "liste_noire_train", "liste_noire_test"]:
    try:
        copier_table_complete(t)
    except Exception as e:
        print(f"        SKIP {t} : {str(e)[:80]}")

print("\n[5/8] Table IMEI ...")
try:
    copier_table_complete("numero_imei")
except Exception as e:
    print(f"        SKIP : {str(e)[:80]}")

print("\n[6/8] Features V2 (echantillon) ...")
copier_features_echantillon("features_msisdn_v2", "liste_noire_fraude", NB_NORMAUX_V2)

print("\n[7/8] Features fresh (echantillon) ...")
copier_features_echantillon("features_msisdn_fresh", "liste_noire_fresh", NB_NORMAUX_FRESH)

print(f"\n[8/8] Termine en {(time.time()-t0)/60:.1f} min")
print("\nVerifie sur Neon : https://console.neon.tech")
