"""
VERIFICATION de l'hypothese de Samar :
Appliquer la regle 'tous les MO depuis la cell 412-54312' (avec >= 3 MO)
aux donnees fresh, et voir si :
  - les 207 vrais fraudeurs sont majoritairement dans cette cellule
  - le resultat se rapproche des 207
"""
import re
import pandas as pd
from sqlalchemy import text
from db_connection import get_engine

CELL_LAC = '412'
CELL_ID = '54312'


def cle(x):
    s = str(x).strip()
    if s.endswith(".0"):
        s = s[:-2]
    d = re.sub(r"\D", "", s)
    return d[-8:] if len(d) >= 8 else d


engine = get_engine()
print("=" * 64)
print(f"  VERIFICATION : regle 'tous MO depuis cell {CELL_LAC}-{CELL_ID}'")
print(f"  sur les donnees fresh (cdr_data_fresh)")
print("=" * 64)

# 1. Diagnostic rapide : la cell existe-t-elle ?
print(f"\n[1] La cell {CELL_LAC}-{CELL_ID} existe-t-elle dans les fresh ?")
with engine.connect() as conn:
    r = conn.execute(text(f"""
        SELECT COUNT(*) AS total_mo, COUNT(DISTINCT msisdn) AS distincts
        FROM cdr_data_fresh
        WHERE call_type = 'mSOriginating'
          AND lac = '{CELL_LAC}' AND cell_id = '{CELL_ID}'
    """))
    row = r.fetchone()
    total_mo, distincts = int(row[0]), int(row[1])

print(f"    Appels MO depuis cette cellule    : {total_mo:,}")
print(f"    Numeros distincts qui y appellent : {distincts:,}")

if distincts == 0:
    print(f"\n  La cellule {CELL_LAC}-{CELL_ID} n'a AUCUNE activite dans les fresh.")
    print(f"  Cette regle ne peut PAS etre appliquee sur le mois de mai 2026.")
    raise SystemExit(0)

# 2. Application de la regle stricte (100% MO depuis cette cell, >= 3 MO)
print(f"\n[2] Numeros dont TOUS les MO viennent de {CELL_LAC}-{CELL_ID} (>= 3 MO)...")
print(f"    (requete GROUP BY sur 213 M lignes - peut prendre 5-15 min)")

with engine.connect() as conn:
    conn.execute(text("SET work_mem = '256MB'"))
    conn.execute(text("SET max_parallel_workers_per_gather = 2"))
    r = conn.execute(text(f"""
        SELECT msisdn
        FROM cdr_data_fresh
        WHERE call_type = 'mSOriginating'
        GROUP BY msisdn
        HAVING COUNT(*) FILTER (WHERE lac = '{CELL_LAC}' AND cell_id = '{CELL_ID}') = COUNT(*)
           AND COUNT(*) >= 3
    """))
    cell_msisdn = [row[0] for row in r.fetchall()]

cell_keys = set(cle(v) for v in cell_msisdn)
print(f"    Total : {len(cell_keys)} numeros respectent la regle stricte")

# 3. Charger les listes a comparer
ent_keys = set(
    cle(v) for v in pd.read_sql("SELECT msisdn FROM liste_entreprise", engine)["msisdn"]
)
fresh_keys = set(
    cle(v) for v in pd.read_sql("SELECT msisdn FROM liste_noire_fresh", engine)["msisdn"]
)

# 4. Comparaisons
in_ent = cell_keys & ent_keys
in_fresh = cell_keys & fresh_keys
both = cell_keys & ent_keys & fresh_keys
ent_in_cell = ent_keys & cell_keys
fresh_only = fresh_keys - ent_keys
ent_only = ent_keys - fresh_keys

print(f"\n[3] Comparaisons :")
print(f"    Liste entreprise (207)        : {len(ent_keys)}")
print(f"    Liste fresh modele (210)      : {len(fresh_keys)}")
print(f"    Cell 412-54312 (regle stricte): {len(cell_keys)}")

print(f"\n[4] Croisements :")
print(f"    Cell 412 ∩ entreprise (207)   : {len(in_ent)} / {len(cell_keys)}")
print(f"    Cell 412 ∩ liste_noire_fresh  : {len(in_fresh)} / {len(cell_keys)}")
print(f"    Cell 412 ∩ ent ∩ fresh        : {len(both)}")

print(f"\n[5] Vue inverse :")
print(f"    Sur les 207 vrais fraudeurs, combien sont dans la cell 412-54312 ?")
print(f"    -> {len(ent_in_cell)} / 207 = {len(ent_in_cell)/207*100:.1f}%")

# 6. Verdict
print(f"\n" + "=" * 64)
if len(ent_in_cell) >= 150:
    print(f"  ==> HYPOTHESE CONFIRMEE")
    print(f"  La grande majorite des vrais fraudeurs sont dans la cell 412-54312.")
    print(f"  Filtrer sur cette cellule + le modele = resultat tres proche des 207 reels.")
elif len(ent_in_cell) >= 50:
    print(f"  ==> HYPOTHESE PARTIELLEMENT VRAIE")
    print(f"  Une partie significative des fraudeurs sont dans la cell.")
    print(f"  Le filtre cell aiderait mais ne couvrirait pas tous les cas.")
else:
    print(f"  ==> HYPOTHESE INFIRMEE")
    print(f"  Peu de vrais fraudeurs sont dans la cell 412-54312 sur ce mois.")
    print(f"  Les fraudeurs de mai 2026 sont disperses sur d'autres cellules.")
    print(f"  Cette regle (specifique aux anciennes donnees) ne s'applique pas ici.")
print("=" * 64)

# 7. Sauvegarder le resultat
with open("../data/verif_cell_412.txt", "w") as f:
    f.write(f"Verification cell {CELL_LAC}-{CELL_ID} sur donnees fresh\n")
    f.write(f"=========================================\n\n")
    f.write(f"Cell active : {distincts:,} numeros (total {total_mo:,} MO)\n")
    f.write(f"Numeros respectant regle stricte : {len(cell_keys)}\n")
    f.write(f"Sur les 207 entreprise, {len(ent_in_cell)} sont dans cette cell\n")
    f.write(f"Sur les 210 fresh, {len(in_fresh)} sont dans cette cell\n")

print(f"\nResultat ecrit dans : data/verif_cell_412.txt")
print(f"\nTermine !")
