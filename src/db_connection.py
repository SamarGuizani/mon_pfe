"""
Module de connexion reutilisable pour tous les scripts du projet.
Detecte automatiquement l'IP de Windows depuis WSL.
"""
import subprocess
import psycopg
from sqlalchemy import create_engine, text

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
    """Retourne un SQLAlchemy engine connecte a PostgreSQL Windows"""
    ip = trouver_ip_windows()
    conn_string = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{ip}:{DB_PORT}/{DB_NAME}"
    return create_engine(conn_string)
