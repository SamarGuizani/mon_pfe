import pandas as pd
import subprocess
import psycopg
from sqlalchemy import create_engine, text
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================
DB_USER = "postgres"
DB_PASSWORD = "samar123"
DB_PORT = "5432"
DB_NAME = "postgres"          # cdr_data est dans la base "postgres" sur Windows

# Seuils de detection
SEUIL_APPELS = 50

# ============================================================
# DETECTION AUTOMATIQUE DE L'IP WINDOWS DEPUIS WSL
# ============================================================
# Probleme : l'IP de Windows change a chaque redemarrage du PC
# Solution : on recupere la passerelle WSL (= adresse Windows)
#
# On utilise psycopg (v3) au lieu de psycopg2 car psycopg2
# plante quand le serveur Windows envoie des messages en francais
# (accents = erreur UTF-8). psycopg3 gere ca correctement.

def trouver_ip_windows():
    """Trouve automatiquement l'IP de Windows depuis WSL"""
    candidats = []

    # Methode 1 : passerelle par defaut (ip route) = IP Windows dans le reseau WSL
    try:
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True, text=True, timeout=5
        )
        gateway = result.stdout.split()[2]
        candidats.append(gateway)
    except Exception:
        pass

    # Methode 2 : resolv.conf (DNS WSL pointe vers Windows)
    try:
        with open("/etc/resolv.conf") as f:
            for line in f:
                if line.startswith("nameserver"):
                    candidats.append(line.split()[1])
                    break
    except Exception:
        pass

    # Methode 3 : localhost (si WSL port forwarding est actif)
    candidats.append("localhost")

    # On teste chaque candidat avec psycopg3 (pas psycopg2 !)
    for ip in candidats:
        try:
            conn = psycopg.connect(
                host=ip, port=DB_PORT,
                user=DB_USER, password=DB_PASSWORD, dbname=DB_NAME,
                connect_timeout=3
            )
            conn.close()
            print(f"      Windows trouve a : {ip}")
            return ip
        except Exception:
            print(f"      {ip} ... non disponible")
            continue

    raise ConnectionError("Impossible de trouver PostgreSQL sur Windows")


print("[0/5] Recherche du serveur Windows...")
DB_HOST = trouver_ip_windows()

# On utilise psycopg (v3) comme driver SQLAlchemy au lieu de psycopg2
# "postgresql+psycopg://" = SQLAlchemy + psycopg3
conn_string = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ============================================================
# ARCHITECTURE RESEAU :
#   [Linux WSL] ----(reseau virtuel)----> [Windows]
#    Python ici                            PostgreSQL + TimescaleDB ici
#    Recoit le resultat                    Fait le calcul sur 741M lignes
#
# Python envoie juste la requete SQL (quelques octets).
# PostgreSQL calcule et renvoie le resultat (quelques Ko).
# Les 83 Go ne bougent JAMAIS vers Linux !
# ============================================================

try:
    engine = create_engine(conn_string)

    with engine.connect() as conn:
        print("Connexion a la base de donnees reussie.")
        print("Base : cdr_data (741M lignes / 83 Go)\n")

        # ----------------------------------------------------------
        # ETAPE 1 : Compter combien de lignes on a (verification rapide)
        # ----------------------------------------------------------
        # Pour TimescaleDB (hypertable), on additionne les chunks
        print("[1/5] Estimation du nombre de lignes...")
        result = conn.execute(text("""
            SELECT COALESCE(SUM(c.reltuples)::bigint, 0) AS estimation
            FROM pg_class p
            JOIN pg_inherits i ON i.inhparent = p.oid
            JOIN pg_class c ON c.oid = i.inhrelid
            WHERE p.relname = 'cdr_data'
        """))
        row = result.fetchone()
        estimation = row[0] if row and row[0] else 0
        if estimation == 0:
            result2 = conn.execute(text("""
                SELECT reltuples::bigint FROM pg_class WHERE relname = 'cdr_data'
            """))
            row2 = result2.fetchone()
            estimation = row2[0] if row2 and row2[0] else 0
        print(f"      Estimation : ~{estimation:,} lignes\n")

        # ----------------------------------------------------------
        # ETAPE 2 : PostgreSQL calcule les features (le travail lourd)
        # ----------------------------------------------------------
        print("[2/5] Calcul des features par msisdn (PostgreSQL travaille)...")
        print("      Cela peut prendre quelques minutes sur 741M lignes...\n")

        # HAVING COUNT(*) > seuil : PostgreSQL filtre directement
        query_suspects = text("""
            SELECT
                msisdn,
                COUNT(*) AS nombre_appels,
                COALESCE(SUM(duration_seconds), 0) AS duree_totale_sec,
                ROUND(AVG(duration_seconds)::numeric, 2) AS duree_moyenne,
                ROUND(
                    100.0 * COUNT(*) FILTER (WHERE duration_seconds < 30) / COUNT(*), 2
                ) AS ratio_appels_courts,
                COUNT(DISTINCT called_number) AS nb_destinataires_uniques
            FROM cdr_data
            GROUP BY msisdn
            HAVING COUNT(*) > :seuil
            ORDER BY nombre_appels DESC
        """)

        result = conn.execution_options(stream_results=True).execute(
            query_suspects, {"seuil": SEUIL_APPELS}
        )

        suspects = pd.DataFrame(result.fetchall(), columns=result.keys())

        print(f"[3/5] Analyse terminee.")
        print(f"      Suspects trouves : {len(suspects)}\n")

        if not suspects.empty:
            print(f"=== NUMEROS SUSPECTS (plus de {SEUIL_APPELS} appels) ===")
            print(suspects.to_string(index=False))
            print(f"\nNombre de suspects : {len(suspects)}")

            suspects["date_detection"] = datetime.now()

            # ----------------------------------------------------------
            # ETAPE 4 : Sauvegarder directement dans PostgreSQL
            # ----------------------------------------------------------
            print(f"\n[4/5] Sauvegarde dans liste_noire_fraude...")

            try:
                with engine.begin() as conn_save:
                    conn_save.execute(text("DROP TABLE IF EXISTS liste_noire_fraude"))
                    conn_save.execute(text("""
                        CREATE TABLE liste_noire_fraude AS
                        SELECT
                            msisdn,
                            COUNT(*) AS nombre_appels,
                            COALESCE(SUM(duration_seconds), 0) AS duree_totale_sec,
                            ROUND(AVG(duration_seconds)::numeric, 2) AS duree_moyenne,
                            ROUND(
                                100.0 * COUNT(*) FILTER (WHERE duration_seconds < 30) / COUNT(*), 2
                            ) AS ratio_appels_courts,
                            COUNT(DISTINCT called_number) AS nb_destinataires_uniques,
                            NOW() AS date_detection
                        FROM cdr_data
                        GROUP BY msisdn
                        HAVING COUNT(*) > :seuil
                        ORDER BY nombre_appels DESC
                    """), {"seuil": SEUIL_APPELS})

                print("      Table 'liste_noire_fraude' mise a jour.")

            except Exception as e_save:
                print(f"      Erreur sauvegarde : {e_save}")

            # ----------------------------------------------------------
            # ETAPE 5 : Stats globales (pour ton rapport de PFE)
            # ----------------------------------------------------------
            print(f"\n[5/5] Statistiques globales...")
            result_stats = conn.execute(text("""
                SELECT
                    COUNT(DISTINCT msisdn) AS total_msisdn,
                    COUNT(*) AS total_appels,
                    ROUND(AVG(duration_seconds)::numeric, 2) AS duree_moyenne_globale,
                    MIN(timestamp) AS premier_appel,
                    MAX(timestamp) AS dernier_appel
                FROM cdr_data
            """))
            stats = result_stats.fetchone()
            print(f"      Total MSISDN uniques  : {stats[0]:,}")
            print(f"      Total appels          : {stats[1]:,}")
            print(f"      Duree moyenne globale  : {stats[2]} sec")
            print(f"      Periode : {stats[3]} --> {stats[4]}")

        else:
            print(f"Aucun numero suspect detecte (seuil : {SEUIL_APPELS} appels).")

        print("\nTermine.")

except Exception as e:
    print(f"Erreur : {e}")
