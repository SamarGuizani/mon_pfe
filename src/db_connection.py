"""
Module de connexion reutilisable pour tous les scripts du projet.
- En production (Render) : utilise la variable d'environnement DATABASE_URL (Neon).
- En local (WSL) : detecte automatiquement l'IP de PostgreSQL sur Windows.
"""
import os
import subprocess
import psycopg
from sqlalchemy import create_engine, text

# Charger .env si present (developpement local)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DB_USER = "postgres"
DB_PASSWORD = "samar123"
DB_PORT = "5432"
DB_NAME = "postgres"


def trouver_ip_windows():
    """Trouve automatiquement l'IP de Windows depuis WSL"""
    candidats = []

    # Methode 1 : passerelle par defaut (ip route)
    try:
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True, text=True, timeout=5
        )
        gateway = result.stdout.split()[2]
        candidats.append(gateway)
    except Exception:
        pass

    # Methode 2 : resolv.conf
    try:
        with open("/etc/resolv.conf") as f:
            for line in f:
                if line.startswith("nameserver"):
                    candidats.append(line.split()[1])
                    break
    except Exception:
        pass

    candidats.append("localhost")

    for ip in candidats:
        try:
            conn = psycopg.connect(
                host=ip, port=DB_PORT,
                user=DB_USER, password=DB_PASSWORD, dbname=DB_NAME,
                connect_timeout=3
            )
            conn.close()
            return ip
        except Exception:
            continue

    raise ConnectionError("Impossible de trouver PostgreSQL sur Windows")


def get_engine():
    """Retourne un SQLAlchemy engine.
    - Si DATABASE_URL existe (Render/production)   -> on l'utilise directement.
    - Sinon (developpement WSL)                    -> on detecte l'IP Windows.
    """
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        # Neon donne 'postgresql://...'  -> sqlalchemy attend 'postgresql+psycopg://...'
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return create_engine(db_url, pool_pre_ping=True)

    # Fallback developpement local
    ip = trouver_ip_windows()
    conn_string = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{ip}:{DB_PORT}/{DB_NAME}"
    return create_engine(conn_string)
