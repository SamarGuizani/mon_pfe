"""
Extraire les IMEI (et IMSI) pour chaque numero suspect de liste_noire_fraude.
Cree la table numero_imei (la "carte d'identite" des SIM Box).
Idee : si un autre numero apparait avec le meme IMEI -> meme boitier -> a bloquer.
"""
import time
from sqlalchemy import text
from db_connection import get_engine

engine = get_engine()
print(f"Demarrage extraction IMEI : {time.ctime()}")
print("(scan cdr_data 83 Go / 741M lignes - peut prendre 30 min - 2h)")

with engine.begin() as conn:
    conn.execute(text("SET LOCAL work_mem = '512MB'"))
    conn.execute(text("SET LOCAL max_parallel_workers_per_gather = 4"))
    conn.execute(text("DROP TABLE IF EXISTS numero_imei CASCADE"))
    conn.execute(text("""
        CREATE TABLE numero_imei AS
        SELECT
            msisdn,
            imei,
            imsi,
            COUNT(*) AS nb_appels,
            MIN(timestamp) AS premier_appel,
            MAX(timestamp) AS dernier_appel
        FROM cdr_data
        WHERE msisdn IN (SELECT msisdn FROM liste_noire_fraude)
        GROUP BY msisdn, imei, imsi
    """))
    print(f"Table creee : {time.ctime()}")

with engine.begin() as conn:
    conn.execute(text("CREATE INDEX idx_numero_imei_msisdn ON numero_imei(msisdn)"))
    conn.execute(text("CREATE INDEX idx_numero_imei_imei ON numero_imei(imei)"))

with engine.connect() as conn:
    r = conn.execute(text("""
        SELECT COUNT(*), COUNT(DISTINCT msisdn), COUNT(DISTINCT imei), COUNT(DISTINCT imsi)
        FROM numero_imei
    """))
    n, m, i, ims = r.fetchone()

print(f"\nTermine : {time.ctime()}")
print(f"  Lignes  : {n:,}")
print(f"  MSISDN  : {m}")
print(f"  IMEI distincts : {i}")
print(f"  IMSI distincts : {ims}")
