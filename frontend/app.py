"""
Dashboard Web - Detection de Fraude SIM Box
3 pages : Dashboard / Graphiques / Liste Noire
"""
import sys
sys.path.append("../src")

from flask import Flask, render_template, jsonify, request
from sqlalchemy import text
from db_connection import get_engine

app = Flask(__name__)
engine = get_engine()


# ============================================================
# PAGE 1 : DASHBOARD (stats + graphiques interactifs)
# ============================================================
@app.route("/")
def page_dashboard():
    return render_template("dashboard.html")


# ============================================================
# PAGE 2 : GRAPHIQUES ML (cliquer sur un nom pour voir l'image)
# ============================================================
@app.route("/graphiques")
def page_graphiques():
    return render_template("graphiques.html")


# ============================================================
# PAGE 3 : LISTE NOIRE (table des suspects)
# ============================================================
@app.route("/liste-noire")
def page_liste_noire():
    return render_template("liste_noire.html")


# ============================================================
# API ENDPOINTS
# ============================================================
@app.route("/api/stats")
def api_stats():
    with engine.connect() as conn:
        r = conn.execute(text("SELECT COUNT(*) FROM features_msisdn_v2"))
        total_msisdn = r.fetchone()[0]

        r = conn.execute(text("SELECT COUNT(*) FROM liste_noire_fraude"))
        total_suspects = r.fetchone()[0]

        r = conn.execute(text("""
            SELECT
                ROUND(AVG(nombre_appels)::numeric, 0),
                ROUND(AVG(appels_sortants)::numeric, 0),
                ROUND(AVG(appels_entrants)::numeric, 0),
                ROUND(AVG(avg_duree_sortants)::numeric, 1),
                ROUND(AVG(distinct_locations)::numeric, 0)
            FROM features_msisdn_v2
        """))
        stats = r.fetchone()

    return jsonify({
        "total_msisdn": total_msisdn,
        "total_suspects": total_suspects,
        "taux_fraude": round(100 * total_suspects / total_msisdn, 2),
        "avg_appels": float(stats[0] or 0),
        "avg_sortants": float(stats[1] or 0),
        "avg_entrants": float(stats[2] or 0),
        "avg_duree_sortants": float(stats[3] or 0),
        "avg_locations": float(stats[4] or 0)
    })


@app.route("/api/suspects")
def api_suspects():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", "", type=str)
    offset = (page - 1) * per_page

    with engine.connect() as conn:
        where = ""
        params = {"limit": per_page, "offset": offset}
        if search:
            where = "WHERE msisdn LIKE :search"
            params["search"] = f"%{search}%"

        r = conn.execute(text(f"SELECT COUNT(*) FROM liste_noire_fraude {where}"), params)
        total = r.fetchone()[0]

        r = conn.execute(text(f"""
            SELECT msisdn, nombre_appels, duree_totale_sec,
                   ratio_appels_courts, nb_imei_utilises,
                   nb_cellules_uniques, appels_par_jour,
                   date_detection
            FROM liste_noire_fraude
            {where}
            ORDER BY nombre_appels DESC
            LIMIT :limit OFFSET :offset
        """), params)

        suspects = []
        for row in r.fetchall():
            suspects.append({
                "msisdn": row[0],
                "nombre_appels": row[1],
                "duree_totale": row[2],
                "ratio_courts": float(row[3] or 0),
                "nb_imei": row[4],
                "nb_cellules": row[5],
                "appels_jour": float(row[6] or 0),
                "date_detection": str(row[7]) if row[7] else ""
            })

    return jsonify({
        "suspects": suspects,
        "total": total,
        "page": page,
        "pages": (total + per_page - 1) // per_page
    })


@app.route("/api/top_suspects")
def api_top_suspects():
    with engine.connect() as conn:
        r = conn.execute(text("""
            SELECT msisdn, nombre_appels, appels_par_jour,
                   ratio_appels_courts, nb_cellules_uniques
            FROM liste_noire_fraude
            ORDER BY nombre_appels DESC
            LIMIT 10
        """))
        top = []
        for row in r.fetchall():
            top.append({
                "msisdn": row[0][-6:],
                "appels": row[1],
                "appels_jour": float(row[2] or 0),
                "ratio_courts": float(row[3] or 0),
                "cellules": row[4]
            })
    return jsonify(top)


@app.route("/api/distribution")
def api_distribution():
    with engine.connect() as conn:
        r = conn.execute(text("""
            SELECT
                CASE
                    WHEN nombre_appels <= 10 THEN '1-10'
                    WHEN nombre_appels <= 50 THEN '11-50'
                    WHEN nombre_appels <= 100 THEN '51-100'
                    WHEN nombre_appels <= 500 THEN '101-500'
                    WHEN nombre_appels <= 1000 THEN '501-1000'
                    ELSE '1000+'
                END AS tranche,
                COUNT(*) AS nb
            FROM features_msisdn_v2
            GROUP BY 1
            ORDER BY MIN(nombre_appels)
        """))
        data = [{"tranche": row[0], "count": row[1]} for row in r.fetchall()]
    return jsonify(data)


if __name__ == "__main__":
    print("\n  Dashboard SIM Box Fraud Detection")
    print("  Page 1 : http://localhost:5000")
    print("  Page 2 : http://localhost:5000/graphiques")
    print("  Page 3 : http://localhost:5000/liste-noire\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
