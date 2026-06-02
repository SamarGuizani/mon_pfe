"""
Configuration email pour l'envoi de codes de verification.

- En local : les vraies valeurs sont lues depuis le fichier .env (non versionne)
- En production (Render) : les valeurs viennent des variables d'environnement du dashboard Render
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
MAIL_DEFAULT_SENDER = ("SIM Box Fraud Detection", MAIL_USERNAME)
