"""
Dashboard Web - Detection de Fraude SIM Box
Auth : Sign Up (email) → Verification code → Sign In → Dashboard
Roles : admin (tout) / analyst (lecture seule)
"""
import sys
sys.path.append("../src")

import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text
from db_connection import get_engine
from email_config import MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USERNAME, MAIL_PASSWORD
import joblib
import pandas as pd
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score

app = Flask(__name__)
app.secret_key = "simbox_pfe_samar_2026"
engine = get_engine()

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "page_login"

# Charger le modele XGBoost au demarrage
# V2 = modele retenu : prouve sur les donnees fresh (F1 = 0.998 sur un mois neuf)
print("  Chargement du modele XGBoost V3...")
model_xgb = joblib.load("../models/xgboost_fraud_v3.pkl")

FEATURES = [
    "appels_sortants", "appels_entrants",
    "duree_sortants", "duree_entrants",
    "avg_duree_sortants", "avg_duree_entrants",
    "variance_sortants", "variance_entrants",
    "location_count", "location_count_sortants", "location_count_entrants",
    "active_hours", "distinct_imei",
    "unique_called", "unique_calling", "nb_jours_actifs"
]


# ============================================================
# ENVOI D'EMAIL
# ============================================================
def send_email(to_email, subject, body_html):
    """Envoie un email via Gmail SMTP avec timeout (evite que Render hang)"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"SIM Box Fraud Detection <{MAIL_USERNAME}>"
    msg["To"] = to_email
    msg.attach(MIMEText(body_html, "html"))

    with smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=15) as server:
        server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.sendmail(MAIL_USERNAME, to_email, msg.as_string())


def generate_code():
    """Genere un code de verification a 6 chiffres"""
    return str(random.randint(100000, 999999))


def log_action(user_id, email, username, role, action):
    """Enregistre chaque action dans la table login_history"""
    ip = request.remote_addr or "unknown"
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO login_history (user_id, email, username, role, action, ip_address)
            VALUES (:uid, :email, :username, :role, :action, :ip)
        """), {"uid": user_id, "email": email, "username": username,
               "role": role, "action": action, "ip": ip})


# ============================================================
# AUTHENTIFICATION
# ============================================================
class User(UserMixin):
    def __init__(self, id, email, username, role):
        self.id = id
        self.email = email
        self.username = username
        self.role = role

    @property
    def is_admin(self):
        return self.role == "admin"


@login_manager.user_loader
def load_user(user_id):
    with engine.connect() as conn:
        r = conn.execute(text("SELECT id, email, username, role FROM users WHERE id = :id"), {"id": int(user_id)})
        row = r.fetchone()
        if row:
            return User(row[0], row[1], row[2], row[3])
    return None


# ============================================================
# SIGN UP (inscription)
# ============================================================
@app.route("/signup", methods=["GET", "POST"])
def page_signup():
    if current_user.is_authenticated:
        return redirect(url_for("page_dashboard"))

    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "analyst")

        if not email or not username or not password:
            error = "Tous les champs sont obligatoires"
        elif len(password) < 6:
            error = "Le mot de passe doit contenir au moins 6 caracteres"
        else:
            with engine.connect() as conn:
                r = conn.execute(text("SELECT id FROM users WHERE email = :e"), {"e": email})
                if r.fetchone():
                    error = "Cet email est deja utilise"

            if not error:
                code = generate_code()
                password_hash = generate_password_hash(password)

                with engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO users (email, username, password_hash, role, is_verified, verification_code)
                        VALUES (:email, :username, :hash, :role, FALSE, :code)
                    """), {
                        "email": email, "username": username,
                        "hash": password_hash, "role": role, "code": code
                    })

                log_action(None, email, username, role, "signup")

                # Envoyer le code par email
                try:
                    send_email(email,
                        "Code de verification - SIM Box Fraud Detection",
                        f"""
                        <div style="font-family:Arial; max-width:400px; margin:auto; padding:30px; background:#1a2332; color:#e0e6ed; border-radius:10px;">
                            <h2 style="color:#00d4ff; text-align:center;">Verification de votre compte</h2>
                            <p>Bonjour <strong>{username}</strong>,</p>
                            <p>Votre code de verification est :</p>
                            <div style="text-align:center; margin:20px 0;">
                                <span style="font-size:36px; font-weight:bold; color:#00d4ff; letter-spacing:8px;">{code}</span>
                            </div>
                            <p style="color:#7a8fa6; font-size:12px;">Ce code expire dans 10 minutes.</p>
                            <hr style="border-color:#2a3a4e;">
                            <p style="color:#7a8fa6; font-size:11px; text-align:center;">SIM Box Fraud Detection - PFE 2026</p>
                        </div>
                        """
                    )
                    return redirect(url_for("page_verify", email=email))
                except Exception as e:
                    error = f"Erreur d'envoi email : {e}"

    return render_template("signup.html", error=error)


# ============================================================
# VERIFY EMAIL (verification du code)
# ============================================================
@app.route("/verify", methods=["GET", "POST"])
def page_verify():
    email = request.args.get("email", "") or request.form.get("email", "")
    error = None
    success = None

    if request.method == "POST":
        code = request.form.get("code", "").strip()
        email = request.form.get("email", "").strip()

        with engine.connect() as conn:
            r = conn.execute(text("""
                SELECT id, verification_code FROM users
                WHERE email = :e AND is_verified = FALSE
            """), {"e": email})
            row = r.fetchone()

        if row and row[1] == code:
            with engine.begin() as conn:
                conn.execute(text("""
                    UPDATE users SET is_verified = TRUE, verification_code = NULL
                    WHERE id = :id
                """), {"id": row[0]})
            success = "Compte verifie ! Vous pouvez maintenant vous connecter."
            return render_template("verify.html", email=email, error=None, success=success)
        else:
            error = "Code incorrect. Verifiez votre email."

    return render_template("verify.html", email=email, error=error, success=success)


# ============================================================
# SIGN IN (connexion)
# ============================================================
@app.route("/login", methods=["GET", "POST"])
def page_login():
    if current_user.is_authenticated:
        return redirect(url_for("page_dashboard"))

    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        with engine.connect() as conn:
            r = conn.execute(text("""
                SELECT id, email, username, password_hash, role, is_verified
                FROM users WHERE email = :e
            """), {"e": email})
            row = r.fetchone()

        if not row:
            error = "Email non trouve. Inscrivez-vous d'abord."
        elif not row[5]:
            error = "Compte non verifie. Verifiez votre email."
            return redirect(url_for("page_verify", email=email))
        elif not check_password_hash(row[3], password):
            error = "Mot de passe incorrect"
        else:
            user = User(row[0], row[1], row[2], row[4])
            login_user(user)
            log_action(row[0], row[1], row[2], row[4], "login")
            return redirect(url_for("page_dashboard"))

    return render_template("login.html", error=error)


# ============================================================
# FORGOT PASSWORD (mot de passe oublie)
# ============================================================
@app.route("/forgot-password", methods=["GET", "POST"])
def page_forgot_password():
    error = None
    success = None

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        with engine.connect() as conn:
            r = conn.execute(text("SELECT id, username FROM users WHERE email = :e AND is_verified = TRUE"), {"e": email})
            row = r.fetchone()

        if not row:
            error = "Email non trouve ou compte non verifie"
        else:
            code = generate_code()
            with engine.begin() as conn:
                conn.execute(text("UPDATE users SET reset_code = :code WHERE id = :id"),
                             {"code": code, "id": row[0]})

            try:
                send_email(email,
                    "Reinitialisation du mot de passe - SIM Box Fraud Detection",
                    f"""
                    <div style="font-family:Arial; max-width:400px; margin:auto; padding:30px; background:#1a2332; color:#e0e6ed; border-radius:10px;">
                        <h2 style="color:#ff4757; text-align:center;">Reinitialisation du mot de passe</h2>
                        <p>Bonjour <strong>{row[1]}</strong>,</p>
                        <p>Votre code de reinitialisation est :</p>
                        <div style="text-align:center; margin:20px 0;">
                            <span style="font-size:36px; font-weight:bold; color:#ff4757; letter-spacing:8px;">{code}</span>
                        </div>
                        <p style="color:#7a8fa6; font-size:12px;">Si vous n'avez pas demande cette reinitialisation, ignorez cet email.</p>
                    </div>
                    """
                )
                return redirect(url_for("page_reset_password", email=email))
            except Exception as e:
                error = f"Erreur d'envoi email : {e}"

    return render_template("forgot_password.html", error=error, success=success)


# ============================================================
# RESET PASSWORD (nouveau mot de passe)
# ============================================================
@app.route("/reset-password", methods=["GET", "POST"])
def page_reset_password():
    email = request.args.get("email", "") or request.form.get("email", "")
    error = None
    success = None

    if request.method == "POST":
        code = request.form.get("code", "").strip()
        new_password = request.form.get("new_password", "")
        email = request.form.get("email", "").strip()

        if len(new_password) < 6:
            error = "Le mot de passe doit contenir au moins 6 caracteres"
        else:
            with engine.connect() as conn:
                r = conn.execute(text("SELECT id, reset_code FROM users WHERE email = :e"), {"e": email})
                row = r.fetchone()

            if row and row[1] == code:
                with engine.begin() as conn:
                    conn.execute(text("""
                        UPDATE users SET password_hash = :hash, reset_code = NULL
                        WHERE id = :id
                    """), {"hash": generate_password_hash(new_password), "id": row[0]})
                success = "Mot de passe change ! Vous pouvez vous connecter."
                return render_template("reset_password.html", email=email, error=None, success=success)
            else:
                error = "Code incorrect"

    return render_template("reset_password.html", email=email, error=error, success=success)


# ============================================================
# LOGOUT
# ============================================================
@app.route("/logout")
@login_required
def page_logout():
    log_action(current_user.id, current_user.email, current_user.username, current_user.role, "logout")
    logout_user()
    return redirect(url_for("page_login"))


# ============================================================
# PAGES PROTEGEES
# ============================================================
@app.route("/")
@login_required
def page_dashboard():
    return render_template("dashboard.html")

@app.route("/resultats-ml")
@login_required
def page_resultats_ml():
    return render_template("resultats_ml.html")

@app.route("/prediction")
@login_required
def page_prediction():
    return render_template("prediction.html")

@app.route("/graphiques")
@login_required
def page_graphiques():
    return render_template("graphiques.html")

@app.route("/liste-noire")
@login_required
def page_liste_noire():
    return render_template("liste_noire.html")

@app.route("/fraud-rules")
@login_required
def page_fraud_rules():
    return render_template("fraud_rules.html")

@app.route("/verification-manuelle")
@login_required
def page_verification_manuelle():
    if not current_user.is_admin:
        return redirect(url_for("page_dashboard"))
    return render_template("verification_manuelle.html")

@app.route("/liste-noire-train")
@login_required
def page_liste_noire_train():
    return render_template("liste_noire_train.html")

@app.route("/liste-noire-test")
@login_required
def page_liste_noire_test():
    return render_template("liste_noire_test.html")


# API pour liste_noire_train
@app.route("/api/suspects-train")
@login_required
def api_suspects_train():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", "", type=str)
    offset = (page - 1) * per_page
    with engine.connect() as conn:
        where, params = "", {"limit": per_page, "offset": offset}
        if search:
            where = "WHERE msisdn LIKE :search"
            params["search"] = f"%{search}%"
        r = conn.execute(text(f"SELECT COUNT(*) FROM liste_noire_train {where}"), params)
        total = r.fetchone()[0]
        r = conn.execute(text(f"""
            SELECT msisdn, appels_sortants, appels_entrants, variance_sortants, variance_entrants,
                   duree_sortants, duree_entrants, location_count, active_hours, distinct_imei,
                   unique_called, unique_calling, nb_jours_actifs
            FROM liste_noire_train {where} ORDER BY appels_sortants DESC LIMIT :limit OFFSET :offset
        """), params)
        suspects = [{
            "msisdn": row[0],
            "appels_sortants": row[1], "appels_entrants": row[2],
            "variance_sortants": float(row[3] or 0), "variance_entrants": float(row[4] or 0),
            "duree_sortants": row[5], "duree_entrants": row[6],
            "location_count": row[7], "active_hours": row[8],
            "distinct_imei": row[9],
            "unique_called": row[10], "unique_calling": row[11],
            "nb_jours_actifs": row[12]
        } for row in r.fetchall()]
    return jsonify({"suspects": suspects, "total": total, "page": page,
                     "pages": (total + per_page - 1) // per_page})


# API pour liste_noire_test (avec probabilite XGBoost)
@app.route("/api/suspects-test")
@login_required
def api_suspects_test():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", "", type=str)
    offset = (page - 1) * per_page
    with engine.connect() as conn:
        where, params = "", {"limit": per_page, "offset": offset}
        if search:
            where = "WHERE msisdn LIKE :search"
            params["search"] = f"%{search}%"
        r = conn.execute(text(f"SELECT COUNT(*) FROM liste_noire_test {where}"), params)
        total = r.fetchone()[0]
        r = conn.execute(text(f"""
            SELECT msisdn, appels_sortants, appels_entrants, variance_sortants, variance_entrants,
                   duree_sortants, duree_entrants, location_count, active_hours, distinct_imei,
                   unique_called, unique_calling, nb_jours_actifs, xgb_proba
            FROM liste_noire_test {where} ORDER BY xgb_proba DESC LIMIT :limit OFFSET :offset
        """), params)
        suspects = [{
            "msisdn": row[0],
            "appels_sortants": row[1], "appels_entrants": row[2],
            "variance_sortants": float(row[3] or 0), "variance_entrants": float(row[4] or 0),
            "duree_sortants": row[5], "duree_entrants": row[6],
            "location_count": row[7], "active_hours": row[8],
            "distinct_imei": row[9],
            "unique_called": row[10], "unique_calling": row[11],
            "nb_jours_actifs": row[12],
            "xgb_proba": float(row[13] or 0)
        } for row in r.fetchall()]
    return jsonify({"suspects": suspects, "total": total, "page": page,
                     "pages": (total + per_page - 1) // per_page})


# API pour les metriques V2
@app.route("/api/metrics-v3")
@login_required
def api_metrics_v3_alias():
    return api_metrics_v3()

@app.route("/api/metrics-v2")
@login_required
def api_metrics_v3():
    import json
    try:
        with open("../data/metrics_v2.json") as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# API : VERIFICATION MANUELLE (admin entre CDR fraudes confirmes)
# ============================================================
@app.route("/api/fraudes-confirmees", methods=["GET", "POST"])
@login_required
def api_fraudes_confirmees():
    if not current_user.is_admin:
        return jsonify({"error": "Acces refuse"}), 403

    if request.method == "POST":
        data = request.get_json()
        msisdn = data.get("msisdn", "").strip()
        source = data.get("source", "").strip()
        commentaire = data.get("commentaire", "").strip()
        type_entree = data.get("type", "fraude").strip()  # 'fraude' ou 'faux_positif'

        if not msisdn:
            return jsonify({"error": "MSISDN requis"}), 400
        if type_entree not in ("fraude", "faux_positif"):
            type_entree = "fraude"

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO fraudes_confirmees_manuelle (msisdn, source, commentaire, ajoute_par, type)
                VALUES (:m, :s, :c, :u, :t)
            """), {"m": msisdn, "s": source, "c": commentaire, "u": current_user.username, "t": type_entree})

        return jsonify({"success": True})

    # GET : liste des fraudes confirmees + faux positifs
    with engine.connect() as conn:
        r = conn.execute(text("""
            SELECT id, msisdn, source, commentaire, ajoute_par, date_ajout, COALESCE(type, 'fraude') AS type
            FROM fraudes_confirmees_manuelle
            ORDER BY date_ajout DESC
        """))
        rows = r.fetchall()

    return jsonify({
        "fraudes": [{
            "id": row[0], "msisdn": row[1], "source": row[2] or "",
            "commentaire": row[3] or "", "ajoute_par": row[4],
            "date_ajout": str(row[5])[:19],
            "type": row[6]
        } for row in rows],
        "total": len(rows)
    })


@app.route("/api/suspects-suggestions")
@login_required
def api_suspects_suggestions():
    """Suggere les TOP suspects de la liste noire (pour autocomplete)"""
    with engine.connect() as conn:
        r = conn.execute(text("""
            SELECT msisdn, appels_sortants, variance_sortants, location_count, distinct_imei
            FROM liste_noire_fraude
            ORDER BY appels_sortants DESC
            LIMIT 50
        """))
        return jsonify([{
            "msisdn": row[0],
            "appels_sortants": row[1],
            "variance_sortants": float(row[2] or 0),
            "location_count": row[3],
            "distinct_imei": row[4]
        } for row in r.fetchall()])


@app.route("/api/fraudes-confirmees/<int:fid>", methods=["DELETE"])
@login_required
def api_supprimer_fraude(fid):
    if not current_user.is_admin:
        return jsonify({"error": "Acces refuse"}), 403

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM fraudes_confirmees_manuelle WHERE id = :id"), {"id": fid})
    return jsonify({"success": True})

@app.route("/users")
@login_required
def page_users():
    if not current_user.is_admin:
        return redirect(url_for("page_dashboard"))
    return render_template("users.html")


# ============================================================
# API : VERIFICATION MANUELLE (admin only)
# ============================================================
@app.route("/api/verify", methods=["POST"])
@login_required
def api_verify():
    if not current_user.is_admin:
        return jsonify({"error": "Acces refuse. Admin uniquement."}), 403
    data = request.get_json()
    msisdn = data.get("msisdn", "")
    statut = data.get("statut", "")
    commentaire = data.get("commentaire", "")
    if statut not in ("confirme", "faux_positif"):
        return jsonify({"error": "Statut invalide"}), 400
    with engine.begin() as conn:
        # Supprimer l'ancien statut si existe
        conn.execute(text("DELETE FROM verification_fraude WHERE msisdn = :m"), {"m": msisdn})
        conn.execute(text("""
            INSERT INTO verification_fraude (msisdn, statut, commentaire, verifie_par)
            VALUES (:m, :s, :c, :u)
        """), {"m": msisdn, "s": statut, "c": commentaire, "u": current_user.username})
    return jsonify({"success": True, "msisdn": msisdn, "statut": statut})


@app.route("/api/verification-stats")
@login_required
def api_verification_stats():
    with engine.connect() as conn:
        r = conn.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE statut = 'confirme') AS confirmes,
                COUNT(*) FILTER (WHERE statut = 'faux_positif') AS faux_positifs,
                COUNT(*) AS total_verifies
            FROM verification_fraude
        """))
        row = r.fetchone()
    return jsonify({"confirmes": row[0], "faux_positifs": row[1], "total_verifies": row[2]})


# ============================================================
# API : GESTION UTILISATEURS (admin only)
# ============================================================
@app.route("/api/users")
@login_required
def api_users():
    if not current_user.is_admin:
        return jsonify({"error": "Acces refuse"}), 403
    with engine.connect() as conn:
        r = conn.execute(text("""
            SELECT id, email, username, role, is_verified, created_at
            FROM users ORDER BY id
        """))
        users = [{"id": row[0], "email": row[1], "username": row[2],
                   "role": row[3], "verified": row[4],
                   "created": str(row[5])[:19] if row[5] else ""}
                  for row in r.fetchall()]
    return jsonify(users)


@app.route("/api/users/delete", methods=["POST"])
@login_required
def api_delete_user():
    if not current_user.is_admin:
        return jsonify({"error": "Acces refuse"}), 403
    data = request.get_json()
    user_id = data.get("id")
    if user_id == current_user.id:
        return jsonify({"error": "Vous ne pouvez pas supprimer votre propre compte"}), 400
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM login_history WHERE user_id = :id"), {"id": user_id})
        conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
    return jsonify({"success": True})


@app.route("/api/users/change-role", methods=["POST"])
@login_required
def api_change_role():
    if not current_user.is_admin:
        return jsonify({"error": "Acces refuse"}), 403
    data = request.get_json()
    user_id = data.get("id")
    new_role = data.get("role")
    if new_role not in ("admin", "analyst"):
        return jsonify({"error": "Role invalide"}), 400
    with engine.begin() as conn:
        conn.execute(text("UPDATE users SET role = :r WHERE id = :id"), {"r": new_role, "id": user_id})
    return jsonify({"success": True})


# ============================================================
# API ENDPOINTS (inchanges - tous @login_required)
# ============================================================
@app.route("/api/stats")
@login_required
def api_stats():
    # Valeur reelle de la grande base CDR (entrainement original sur 741M lignes)
    # On garde cette valeur fixe car en prod la base Neon est un echantillon
    TOTAL_MSISDN_PROD = 4_282_822

    with engine.connect() as conn:
        r = conn.execute(text("SELECT COUNT(*) FROM features_msisdn_v2"))
        total_msisdn_sample = r.fetchone()[0]
        # Si on est sur l'echantillon Neon (< 1M) on affiche la vraie valeur prod
        total_msisdn = TOTAL_MSISDN_PROD if total_msisdn_sample < 1_000_000 else total_msisdn_sample
        r = conn.execute(text("SELECT COUNT(*) FROM liste_noire_fraude"))
        total_suspects = r.fetchone()[0]
        r = conn.execute(text("""
            SELECT ROUND(AVG(appels_sortants + appels_entrants)::numeric,0),
                   ROUND(AVG(appels_sortants)::numeric,0),
                   ROUND(AVG(appels_entrants)::numeric,0),
                   ROUND(AVG(avg_duree_sortants)::numeric,1),
                   ROUND(AVG(location_count)::numeric,0)
            FROM features_msisdn_v2
        """))
        stats = r.fetchone()
    return jsonify({
        "total_msisdn": total_msisdn, "total_suspects": total_suspects,
        "taux_fraude": round(100 * total_suspects / total_msisdn, 4),
        "avg_appels": float(stats[0] or 0), "avg_sortants": float(stats[1] or 0),
        "avg_entrants": float(stats[2] or 0), "avg_duree_sortants": float(stats[3] or 0),
        "avg_locations": float(stats[4] or 0)
    })

@app.route("/api/ml-info")
@login_required
def api_ml_info():
    """Lit les metriques V3 directement (pas de fichier CSV)"""
    import json
    try:
        with open("../data/metrics_v2.json") as f:
            m = json.load(f)
        return jsonify({
            "train_total": m["train_size"],
            "train_fraude": m["train_fraudes"],
            "train_normal": m["train_size"] - m["train_fraudes"],
            "train_pct": 70,
            "test_total": m["test_size"],
            "test_fraude": m["test_fraudes"],
            "test_normal": m["test_size"] - m["test_fraudes"],
            "test_pct": 30,
            "features": FEATURES, "model_name": "XGBoost V2", "status": "pret"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/run-test", methods=["POST"])
@login_required
def api_run_test():
    """Retourne les metriques V3 deja calculees (rapide)"""
    import json
    try:
        with open("../data/metrics_v2.json") as f:
            m = json.load(f)
        return jsonify({
            "total_test": m["test_size"],
            "confusion_matrix": m["confusion_matrix"],
            "precision": round(m["precision"], 4),
            "recall": round(m["recall"], 4),
            "f1": round(m["f1"], 4),
            "auc": round(m["auc"], 4),
            "fraudes_detectees": m["fraudes_detectees_test"],
            "fraudes_reelles": m["test_fraudes"], "status": "termine"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/test-fresh")
@login_required
def page_test_fresh():
    return render_template("test_fresh.html")


@app.route("/api/metrics-fresh")
@login_required
def api_metrics_fresh():
    """Resultats du test independant sur les donnees fresh (mai 2026)"""
    import json
    try:
        with open("../data/metrics_fresh.json") as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/comparaison-entreprise")
@login_required
def api_comparaison_entreprise():
    """Comparaison reelle : modele vs liste de l'entreprise (207 vrais)"""
    import json
    try:
        with open("../data/comparaison_entreprise.json") as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/metrics-real")
@login_required
def api_metrics_real():
    """Metriques du modele re-entraine sur les vrais labels"""
    import json
    try:
        with open("../data/metrics_real.json") as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/imei")
@login_required
def page_imei():
    return render_template("imei.html")


@app.route("/api/imei-stats")
@login_required
def api_imei_stats():
    """Statistiques globales sur les IMEI des numeros suspects"""
    try:
        with engine.connect() as conn:
            r = conn.execute(text("""
                SELECT COUNT(*), COUNT(DISTINCT msisdn),
                       COUNT(DISTINCT imei), COUNT(DISTINCT imsi)
                FROM numero_imei
            """))
            total, n_msisdn, n_imei, n_imsi = r.fetchone()
            r = conn.execute(text("""
                SELECT COUNT(*) FROM (
                    SELECT imei FROM numero_imei
                    WHERE imei IS NOT NULL AND imei != ''
                    GROUP BY imei
                    HAVING COUNT(DISTINCT msisdn) > 1
                ) t
            """))
            shared = r.fetchone()[0]
        return jsonify({"ready": True, "total": int(total),
                         "msisdn": int(n_msisdn), "imei": int(n_imei),
                         "imsi": int(n_imsi), "imei_partages": int(shared)})
    except Exception as e:
        return jsonify({"ready": False, "message": str(e)})


@app.route("/api/imei-partages")
@login_required
def api_imei_partages():
    """IMEI utilises par plusieurs MSISDN (= SIM Box)"""
    try:
        with engine.connect() as conn:
            r = conn.execute(text("""
                SELECT imei,
                       COUNT(DISTINCT msisdn) AS nb_msisdn,
                       SUM(nb_appels) AS total_appels,
                       STRING_AGG(DISTINCT msisdn, ', ') AS msisdns
                FROM numero_imei
                WHERE imei IS NOT NULL AND imei != ''
                GROUP BY imei
                HAVING COUNT(DISTINCT msisdn) > 1
                ORDER BY nb_msisdn DESC, total_appels DESC
                LIMIT 100
            """))
            rows = [{"imei": row[0], "nb_msisdn": int(row[1]),
                     "total_appels": int(row[2]), "msisdns": row[3]}
                    for row in r.fetchall()]
        return jsonify({"ready": True, "imei_partages": rows})
    except Exception:
        return jsonify({"ready": False, "imei_partages": []})


@app.route("/api/imei-tous")
@login_required
def api_imei_tous():
    """Tous les couples MSISDN - IMEI (avec pagination)"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", "", type=str)
    offset = (page - 1) * per_page
    try:
        with engine.connect() as conn:
            where, params = "", {"limit": per_page, "offset": offset}
            if search:
                where = "WHERE msisdn LIKE :search OR imei LIKE :search"
                params["search"] = f"%{search}%"
            r = conn.execute(text(f"SELECT COUNT(*) FROM numero_imei {where}"), params)
            total = r.fetchone()[0]
            r = conn.execute(text(f"""
                SELECT msisdn, imei, imsi, nb_appels, premier_appel, dernier_appel
                FROM numero_imei {where}
                ORDER BY msisdn, nb_appels DESC
                LIMIT :limit OFFSET :offset
            """), params)
            rows = [{
                "msisdn": row[0], "imei": row[1] or "", "imsi": row[2] or "",
                "nb_appels": int(row[3] or 0),
                "premier": str(row[4])[:10] if row[4] else "",
                "dernier": str(row[5])[:10] if row[5] else ""
            } for row in r.fetchall()]
        return jsonify({"ready": True, "total": total, "rows": rows,
                         "page": page, "pages": (total + per_page - 1) // per_page})
    except Exception:
        return jsonify({"ready": False, "total": 0, "rows": [], "page": 1, "pages": 0})


@app.route("/api/suspects-fresh")
@login_required
def api_suspects_fresh():
    """Les numeros suspects detectes par le modele sur les donnees fresh"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 15, type=int)
    search = request.args.get("search", "", type=str)
    offset = (page - 1) * per_page
    with engine.connect() as conn:
        where, params = "", {"limit": per_page, "offset": offset}
        if search:
            where = "WHERE msisdn LIKE :search"
            params["search"] = f"%{search}%"
        r = conn.execute(text(f"SELECT COUNT(*) FROM liste_noire_fresh {where}"), params)
        total = r.fetchone()[0]
        r = conn.execute(text(f"""
            SELECT msisdn, appels_sortants, appels_entrants,
                   variance_sortants, variance_entrants,
                   location_count, distinct_imei,
                   active_hours, nb_jours_actifs, xgb_proba
            FROM liste_noire_fresh {where}
            ORDER BY xgb_proba DESC
            LIMIT :limit OFFSET :offset
        """), params)
        suspects = [{
            "msisdn": row[0],
            "appels_sortants": int(row[1] or 0),
            "appels_entrants": int(row[2] or 0),
            "variance_sortants": float(row[3] or 0),
            "variance_entrants": float(row[4] or 0),
            "location_count": int(row[5] or 0),
            "distinct_imei": int(row[6] or 0),
            "active_hours": int(row[7] or 0),
            "nb_jours_actifs": int(row[8] or 0),
            "xgb_proba": float(row[9] or 0),
        } for row in r.fetchall()]
    return jsonify({"suspects": suspects, "total": total, "page": page,
                    "pages": (total + per_page - 1) // per_page})


@app.route("/api/predict-msisdn", methods=["POST"])
@login_required
def api_predict_msisdn():
    data = request.get_json()
    msisdn = data.get("msisdn", "").strip()
    if not msisdn:
        return jsonify({"error": "MSISDN vide"}), 400
    sql_features = """
        SELECT appels_sortants, appels_entrants,
               duree_sortants, duree_entrants,
               avg_duree_sortants, avg_duree_entrants,
               variance_sortants, variance_entrants,
               location_count, location_count_sortants, location_count_entrants,
               active_hours, distinct_imei,
               unique_called, unique_calling, nb_jours_actifs
        FROM {table} WHERE msisdn = :msisdn
    """
    row, source = None, None
    with engine.connect() as conn:
        for table, label in (("features_msisdn_v2", "ancien jeu"),
                             ("features_msisdn_fresh", "test mai 2026")):
            r = conn.execute(text(sql_features.format(table=table)), {"msisdn": msisdn})
            row = r.fetchone()
            if row:
                source = label
                break
    if not row:
        return jsonify({"error": f"MSISDN '{msisdn}' non trouve dans la base"}), 404
    feature_values = [float(v) if v is not None else 0.0 for v in row]
    feature_dict = dict(zip(FEATURES, feature_values))
    X = np.array([feature_values])
    prediction = int(model_xgb.predict(X)[0])
    proba_fraude = float(model_xgb.predict_proba(X)[0][1])
    return jsonify({"msisdn": msisdn, "prediction": "Fraude" if prediction == 1 else "Normal",
                     "probabilite_fraude": round(proba_fraude * 100, 2),
                     "features": feature_dict, "anomalies": {},
                     "source": source})

@app.route("/api/suspects")
@login_required
def api_suspects():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", "", type=str)
    filter_type = request.args.get("filter", "default", type=str)
    offset = (page - 1) * per_page

    # Determiner le tri selon le filtre
    if filter_type == "min_duree":
        # Min duree sortants = les appels les plus courts (robots/SIM Box)
        order_by = "ORDER BY avg_duree_sortants ASC, appels_sortants DESC"
    elif filter_type == "max_variance":
        # Max variance sortants = appelle beaucoup de numeros differents
        order_by = "ORDER BY variance_sortants DESC, appels_sortants DESC"
    elif filter_type == "both":
        # Les 2 combines : calcul d'un score de suspicion
        # Plus la duree est courte ET plus la variance est haute → plus suspect
        order_by = "ORDER BY (variance_sortants - avg_duree_sortants) DESC, appels_sortants DESC"
    else:
        order_by = "ORDER BY appels_sortants DESC"

    with engine.connect() as conn:
        where, params = "", {"limit": per_page, "offset": offset}
        if search:
            where = "WHERE msisdn LIKE :search"
            params["search"] = f"%{search}%"
        r = conn.execute(text(f"SELECT COUNT(*) FROM liste_noire_fraude {where}"), params)
        total = r.fetchone()[0]
        r = conn.execute(text(f"""
            SELECT msisdn, appels_sortants, appels_entrants,
                   duree_sortants, duree_entrants,
                   avg_duree_sortants, avg_duree_entrants,
                   variance_sortants, variance_entrants,
                   location_count, location_count_sortants, location_count_entrants,
                   active_hours, distinct_imei,
                   unique_called, unique_calling, nb_jours_actifs, date_detection
            FROM liste_noire_fraude {where} {order_by} LIMIT :limit OFFSET :offset
        """), params)
        suspects = [{
            "msisdn": row[0],
            "appels_sortants": row[1], "appels_entrants": row[2],
            "duree_sortants": row[3], "duree_entrants": row[4],
            "avg_duree_sortants": float(row[5] or 0), "avg_duree_entrants": float(row[6] or 0),
            "variance_sortants": float(row[7] or 0), "variance_entrants": float(row[8] or 0),
            "location_count": row[9],
            "location_count_sortants": row[10], "location_count_entrants": row[11],
            "active_hours": row[12], "distinct_imei": row[13],
            "unique_called": row[14], "unique_calling": row[15],
            "nb_jours_actifs": row[16],
            "date_detection": str(row[17]) if row[17] else ""
        } for row in r.fetchall()]
    return jsonify({"suspects": suspects, "total": total, "page": page,
                     "pages": (total + per_page - 1) // per_page})

@app.route("/api/top_suspects")
@login_required
def api_top_suspects():
    with engine.connect() as conn:
        r = conn.execute(text("""
            SELECT msisdn, appels_sortants, variance_sortants, location_count, distinct_imei
            FROM liste_noire_fraude ORDER BY appels_sortants DESC LIMIT 10
        """))
        return jsonify([{"msisdn": row[0][-6:], "appels": row[1], "sortants": row[1],
                          "variance": float(row[2] or 0), "locations": row[3],
                          "imei": row[4]} for row in r.fetchall()])

@app.route("/api/distribution")
@login_required
def api_distribution():
    with engine.connect() as conn:
        r = conn.execute(text("""
            SELECT CASE WHEN appels_sortants<=10 THEN '1-10'
                        WHEN appels_sortants<=50 THEN '11-50'
                        WHEN appels_sortants<=100 THEN '51-100'
                        WHEN appels_sortants<=500 THEN '101-500'
                        WHEN appels_sortants<=1000 THEN '501-1000'
                        ELSE '1000+' END AS tranche, COUNT(*) AS nb
            FROM features_msisdn_v2
            WHERE appels_sortants > 0
            GROUP BY 1
            ORDER BY MIN(appels_sortants)
        """))
        return jsonify([{"tranche": row[0], "count": row[1]} for row in r.fetchall()])

@app.route("/api/current-user")
@login_required
def api_current_user():
    return jsonify({"username": current_user.username, "role": current_user.role,
                     "email": current_user.email, "is_admin": current_user.is_admin})


# ============================================================
# ASSISTANT SQL : base de connaissances + construction de requetes
# ============================================================
import unicodedata
import re


def _normaliser_texte(txt):
    """Minuscule + suppression des accents pour comparer les mots-cles"""
    txt = (txt or "").lower().strip()
    txt = unicodedata.normalize("NFD", txt)
    return "".join(c for c in txt if unicodedata.category(c) != "Mn")


# Colonnes numeriques reconnues pour les filtres sur-mesure (mot -> colonne SQL)
COLONNES_SQL = [
    ("variance_sortants", ["variance"]),
    ("distinct_imei", ["imei"]),
    ("location_count", ["cellule", "cellules", "location", "position", "localisation", "lieu"]),
    ("nb_jours_actifs", ["jours actifs", "jours"]),
    ("active_hours", ["heures actives", "heures"]),
    ("appels_entrants", ["appels entrants", "entrants", "entrant"]),
    ("appels_sortants", ["appels sortants", "sortants", "sortant", "appels", "appel"]),
    ("unique_called", ["numeros appeles", "destinataires"]),
]


def _detecter_colonne(q):
    for colonne, mots in COLONNES_SQL:
        if any(m in q for m in mots):
            return colonne
    return None


def _detecter_operateur(q):
    if any(w in q for w in ["plus de", "superieur", "superieure", "au dessus", "depasse",
                            "au moins", "minimum", "elevee", "eleve", "grand", ">"]):
        return ">"
    if any(w in q for w in ["moins de", "inferieur", "inferieure", "en dessous",
                            "maximum", "petit", "faible", "<"]):
        return "<"
    if any(w in q for w in ["egal", "exactement", "vaut", "="]):
        return "="
    return None


def construire_filtre_dynamique(q):
    """Construit une requete SQL sur-mesure si la question contient une condition chiffree."""
    op = _detecter_operateur(q)
    col = _detecter_colonne(q)
    if not op or not col:
        return None
    nombres = [n for n in re.findall(r"\d+", q) if len(n) <= 6]
    if not nombres:
        return None
    seuil = nombres[0]
    if any(w in q for w in ["suspect", "fraude", "noire", "fraudeur"]):
        table = "liste_noire_fraude"
    else:
        table = "features_msisdn_v2"
    sql = (f"SELECT msisdn, {col}\n"
           f"FROM {table}\n"
           f"WHERE {col} {op} {seuil}\n"
           f"ORDER BY {col} DESC;")
    return {
        "titre": f"Filtre sur-mesure : {col} {op} {seuil}",
        "sql": sql,
        "explication": (f"Requete construite a partir de TA question : affiche les numeros de la table "
                        f"{table} dont la colonne {col} est {op} {seuil}, du plus grand au plus petit. "
                        f"Tu peux changer la colonne, le signe ou le nombre directement dans pgAdmin.")
    }


SQL_INTENTS = [
    {
        "titre": "Lister tous les numeros suspects",
        "priorite": -1,
        "keywords": ["lister", "liste", "afficher", "voir", "montrer", "numero", "suspect", "fraude", "fraudeur", "tous"],
        "sql": "SELECT * FROM liste_noire_fraude\nORDER BY appels_sortants DESC;",
        "explication": "Affiche tous les numeros detectes comme suspects (table liste_noire_fraude), du plus actif au moins actif."
    },
    {
        "titre": "Compter le nombre de numeros suspects",
        "keywords": ["compter", "combien", "nombre", "count", "quantite", "suspect", "fraude"],
        "sql": "SELECT COUNT(*) AS nb_suspects FROM liste_noire_fraude;",
        "explication": "Donne le nombre total de numeros presents dans la liste noire."
    },
    {
        "titre": "Telecharger / exporter la liste noire en fichier CSV",
        "keywords": ["telecharger", "exporter", "export", "download", "csv", "fichier", "enregistrer", "sauvegarder", "extraire", "telechargement"],
        "sql": "COPY (SELECT * FROM liste_noire_fraude)\nTO 'C:\\Users\\Public\\liste_noire.csv'\nWITH (FORMAT CSV, HEADER, ENCODING 'UTF8');",
        "explication": "COPY ... TO ecrit un fichier CSV sur le PC ou tourne PostgreSQL (Windows). Choisis un dossier accessible comme C:\\Users\\Public. ASTUCE pgAdmin : tu peux aussi lancer un SELECT, puis cliquer le bouton 'Download as CSV' (raccourci F8) au-dessus du resultat."
    },
    {
        "titre": "Voir les 20 numeros les plus suspects",
        "keywords": ["top", "plus", "pire", "premiers", "classement", "ranking", "actifs", "suspect"],
        "sql": "SELECT msisdn, appels_sortants, variance_sortants, location_count, distinct_imei\nFROM liste_noire_fraude\nORDER BY appels_sortants DESC\nLIMIT 20;",
        "explication": "Affiche les 20 numeros les plus actifs de la liste noire (les plus suspects)."
    },
    {
        "titre": "Voir les features d'un numero precis",
        "keywords": ["feature", "features", "profil", "caracteristique", "caracteristiques"],
        "sql": "SELECT * FROM features_msisdn_v2\nWHERE msisdn = '21690493475';",
        "explication": "Affiche les 16 features calculees pour un numero. Remplace 21690493475 par le numero voulu."
    },
    {
        "titre": "Compter le nombre total de numeros analyses",
        "keywords": ["compter", "combien", "nombre", "total", "analyses", "analyse", "msisdn", "numero"],
        "sql": "SELECT COUNT(*) AS nb_numeros FROM features_msisdn_v2;",
        "explication": "Donne le nombre total de numeros analyses (table features_msisdn_v2)."
    },
    {
        "titre": "Voir un echantillon de la table CDR brute",
        "keywords": ["cdr", "brute", "brutes", "echantillon", "donnees", "raw", "lignes", "ligne"],
        "sql": "SELECT * FROM cdr_data\nLIMIT 100;",
        "explication": "Affiche les 100 premieres lignes des donnees CDR brutes. On met LIMIT pour ne pas charger 741M lignes."
    },
    {
        "titre": "Compter le nombre total d'appels (CDR)",
        "keywords": ["compter", "combien", "nombre", "total", "appels", "appel"],
        "sql": "SELECT COUNT(*) AS nb_appels FROM cdr_data;",
        "explication": "Donne le nombre total d'appels CDR dans la base (long sur 741M lignes)."
    },
    {
        "titre": "Voir tous les appels d'un numero dans les CDR",
        "keywords": ["appels", "appel", "msisdn"],
        "sql": "SELECT * FROM cdr_data\nWHERE msisdn = '21690493475'\nORDER BY \"timestamp\"\nLIMIT 200;",
        "explication": "Affiche les appels d'un numero precis dans les CDR. Remplace 21690493475 par le numero voulu."
    },
    {
        "titre": "Lister la liste noire d'entrainement (train)",
        "keywords": ["train", "entrainement", "apprentissage"],
        "sql": "SELECT * FROM liste_noire_train;",
        "explication": "Affiche les fraudes utilisees pour l'entrainement du modele (70%)."
    },
    {
        "titre": "Lister la liste noire de test",
        "keywords": ["test", "evaluation"],
        "sql": "SELECT * FROM liste_noire_test\nORDER BY xgb_proba DESC;",
        "explication": "Affiche les fraudes detectees par le modele sur le test (30%), triees par probabilite."
    },
    {
        "titre": "Voir la taille des tables (espace disque)",
        "keywords": ["taille", "poids", "espace", "disque", "size", "memoire", "lourde", "lourd"],
        "sql": "SELECT relname AS table_nom,\n       pg_size_pretty(pg_total_relation_size(relid)) AS taille\nFROM pg_catalog.pg_statio_user_tables\nORDER BY pg_total_relation_size(relid) DESC;",
        "explication": "Affiche chaque table avec sa taille sur le disque, de la plus grosse a la plus petite."
    },
    {
        "titre": "Voir toutes les tables de la base",
        "keywords": ["tables", "schema", "base", "existe", "toutes"],
        "sql": "SELECT tablename FROM pg_tables\nWHERE schemaname = 'public'\nORDER BY tablename;",
        "explication": "Affiche la liste de toutes les tables de ta base de donnees."
    },
    {
        "titre": "Voir les utilisateurs du site",
        "keywords": ["utilisateur", "utilisateurs", "user", "users", "compte", "comptes", "admin", "analyst"],
        "sql": "SELECT id, email, username, role, is_verified\nFROM users\nORDER BY id;",
        "explication": "Affiche les comptes utilisateurs du dashboard (admin et analyst)."
    },
    {
        "titre": "Supprimer une table",
        "keywords": ["supprimer", "effacer", "delete", "drop", "detruire", "enlever"],
        "sql": "DROP TABLE IF EXISTS nom_de_la_table;",
        "explication": "Supprime une table. ATTENTION : c'est irreversible. Remplace nom_de_la_table par le vrai nom."
    },
    {
        "titre": "Voir les statistiques moyennes des numeros",
        "keywords": ["moyenne", "moyennes", "moyen", "statistique", "statistiques", "stats"],
        "sql": "SELECT ROUND(AVG(appels_sortants)::numeric, 1) AS moy_sortants,\n       ROUND(AVG(appels_entrants)::numeric, 1) AS moy_entrants,\n       ROUND(AVG(variance_sortants)::numeric, 1) AS moy_variance\nFROM features_msisdn_v2;",
        "explication": "Calcule les moyennes (appels sortants, entrants, variance) sur tous les numeros analyses."
    },
    {
        "titre": "Voir les suspects qui utilisent plusieurs IMEI",
        "keywords": ["plusieurs imei", "multi imei", "imei multiple", "boitier", "boitiers"],
        "sql": "SELECT msisdn, distinct_imei, appels_sortants\nFROM liste_noire_fraude\nWHERE distinct_imei >= 2\nORDER BY distinct_imei DESC;",
        "explication": "Affiche les suspects qui ont utilise au moins 2 IMEI differents (signe typique d'une SIM Box)."
    },
    {
        "titre": "Voir les colonnes (structure) d'une table",
        "keywords": ["colonnes", "colonne", "structure", "champs", "decrire"],
        "sql": "SELECT column_name, data_type\nFROM information_schema.columns\nWHERE table_name = 'liste_noire_fraude';",
        "explication": "Affiche les colonnes et leurs types pour une table. Remplace liste_noire_fraude par la table voulue."
    },
    {
        "titre": "Voir l'historique des connexions au site",
        "keywords": ["connexion", "connexions", "login", "deconnexion", "historique"],
        "sql": "SELECT * FROM login_history\nORDER BY id DESC\nLIMIT 100;",
        "explication": "Affiche les 100 dernieres connexions et actions des utilisateurs du dashboard."
    },
    {
        "titre": "Voir les fraudes confirmees manuellement",
        "keywords": ["confirmee", "confirmees", "confirme", "manuelle", "manuel", "validee", "verifiee"],
        "sql": "SELECT * FROM fraudes_confirmees_manuelle\nORDER BY date_ajout DESC;",
        "explication": "Affiche les numeros que l'admin a confirmes manuellement comme fraude (vrais labels)."
    },
    {
        "titre": "Vider une table (garder la table vide)",
        "keywords": ["vider", "vide", "truncate", "nettoyer"],
        "sql": "TRUNCATE TABLE nom_de_la_table;",
        "explication": "Supprime TOUTES les lignes d'une table mais garde la table (vide). Remplace nom_de_la_table."
    },
    {
        "titre": "Renommer une table",
        "keywords": ["renommer", "renomme", "rename"],
        "sql": "ALTER TABLE ancien_nom\nRENAME TO nouveau_nom;",
        "explication": "Change le nom d'une table. Remplace ancien_nom et nouveau_nom par les vrais noms."
    },
    {
        "titre": "Copier une table dans une nouvelle table",
        "keywords": ["copier", "copie", "dupliquer", "duplique"],
        "sql": "CREATE TABLE copie_de_la_table AS\nSELECT * FROM table_source;",
        "explication": "Cree une nouvelle table identique a une table existante. Pratique avant une modification risquee."
    },
    {
        "titre": "Voir la version de PostgreSQL",
        "keywords": ["version", "postgresql"],
        "sql": "SELECT version();",
        "explication": "Affiche la version exacte de PostgreSQL installee."
    },
]


def chercher_sql(question):
    """Retourne les intents correspondants, tries par score puis priorite"""
    q = _normaliser_texte(question)
    resultats = []
    for intent in SQL_INTENTS:
        score = sum(1 for kw in intent["keywords"] if kw in q)
        if score > 0:
            resultats.append((score, intent.get("priorite", 0), intent))
    resultats.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return resultats


@app.route("/assistant-sql")
@login_required
def page_assistant_sql():
    return render_template("assistant_sql.html")


@app.route("/api/assistant-sql", methods=["POST"])
@login_required
def api_assistant_sql():
    question = request.get_json().get("question", "")
    if not question.strip():
        return jsonify({"error": "Pose une question."}), 400

    q = _normaliser_texte(question)

    # 1. Requete sur-mesure si la question contient une condition chiffree
    filtre = construire_filtre_dynamique(q)

    # 2. Recherche par mots-cles dans la base de connaissances
    resultats = chercher_sql(question)

    # 3. Un MSISDN tape par l'utilisateur (suite de 8 chiffres ou plus)
    msisdn = next((n for n in re.findall(r"\d+", q) if len(n) >= 8), None)
    if msisdn:
        # remonter les intents qui travaillent sur un numero precis
        resultats.sort(key=lambda r: ("21690493475" in r[2]["sql"], r[0], r[1]), reverse=True)

    if not filtre and not resultats:
        if msisdn:
            filtre = {
                "titre": "Voir les features de ce numero",
                "sql": "SELECT * FROM features_msisdn_v2\nWHERE msisdn = '21690493475';",
                "explication": "Affiche les 16 features calculees pour le numero que tu as tape."
            }
        else:
            return jsonify({
                "trouve": False,
                "message": "Je n'ai pas bien compris. Essaie avec des mots comme : lister, compter, "
                           "telecharger, filtrer, suspects, appels, variance, imei, tables, taille... "
                           "ou clique un exemple.",
                "exemples": [i["titre"] for i in SQL_INTENTS]
            })

    if filtre:
        best = filtre
        suggestions = [r[2]["titre"] for r in resultats[:3]]
    else:
        best = resultats[0][2]
        suggestions = [r[2]["titre"] for r in resultats[1:4]]

    # 4. Personnaliser la requete avec ce que l'utilisateur a tape
    sql = best["sql"]
    if msisdn:
        sql = sql.replace("21690493475", msisdn)
    petits = [n for n in re.findall(r"\d+", q) if 1 <= len(n) <= 4]
    if petits and "LIMIT " in sql:
        sql = re.sub(r"LIMIT \d+", "LIMIT " + petits[0], sql)

    return jsonify({
        "trouve": True,
        "titre": best["titre"],
        "sql": sql,
        "explication": best["explication"],
        "suggestions": suggestions
    })


if __name__ == "__main__":
    print("\n  Dashboard SIM Box Fraud Detection")
    print("  http://localhost:5000\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
