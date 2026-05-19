"""
COMPARAISON : liste de l'entreprise (ttdata.xlsx, 207 numeros confirmes)
              VS  liste_noire_fresh (les numeros detectes par le modele).

Version legere : ne charge que les 207 + les 210 numeros (aucun risque pour le serveur).
Ne touche AUCUNE table d'apprentissage. Cree seulement la table liste_entreprise.
"""
import re
import json
import pandas as pd
from sqlalchemy import text
from db_connection import get_engine

FICHIER = "/mnt/c/Users/USER/OneDrive/Desktop/ttdata.xlsx"


def cle(x):
    """Normalise un numero : garde les 8 derniers chiffres (peu importe le format)."""
    s = str(x).strip()
    if s.endswith(".0"):
        s = s[:-2]
    d = re.sub(r"\D", "", s)
    return d[-8:] if len(d) >= 8 else d


print("=" * 64)
print("  COMPARAISON : liste ENTREPRISE  VS  liste_noire_fresh")
print("=" * 64)

# 1. Liste de l'entreprise
ent = pd.read_excel(FICHIER, header=None)
ent_nums = [str(v) for v in ent[0].tolist()]
ent_keys = {}
for v in ent_nums:
    ent_keys[cle(v)] = v
print(f"\n[1] Liste entreprise   : {len(ent_nums)} numeros ({len(ent_keys)} distincts)")

# 2. liste_noire_fresh (detections du modele sur les donnees fresh)
engine = get_engine()
fresh = pd.read_sql("SELECT msisdn FROM liste_noire_fresh", engine)
fresh_keys = set(cle(v) for v in fresh["msisdn"])
print(f"[2] liste_noire_fresh  : {len(fresh)} numeros detectes par le modele")

# 3. Comparaison
ent_set = set(ent_keys.keys())
vp = ent_set & fresh_keys          # entreprise ET detecte
fn = ent_set - fresh_keys          # entreprise mais NON detecte
fp = fresh_keys - ent_set          # detecte mais PAS dans la liste entreprise

precision = len(vp) / len(fresh_keys) * 100 if fresh_keys else 0
recall = len(vp) / len(ent_set) * 100 if ent_set else 0

print("\n" + "=" * 64)
print("  RESULTAT")
print("=" * 64)
print(f"  Numeros confirmes par l'entreprise        : {len(ent_set)}")
print(f"  Numeros detectes par le modele            : {len(fresh_keys)}")
print(f"  >>> EN COMMUN (identiques)                : {len(vp)}")
print(f"  >>> Entreprise NON detectes (manques)     : {len(fn)}")
print(f"  >>> Detectes en PLUS (hors liste)         : {len(fp)}")
print(f"  Precision : {precision:.1f}%   (sur ce que le modele a flague, % de vrais)")
print(f"  Rappel    : {recall:.1f}%   (sur les 207 reels, % attrapes)")

if fn:
    print(f"\n  Les {len(fn)} numeros entreprise NON detectes par le modele :")
    for k in sorted(fn):
        print(f"    {ent_keys[k]}")

# 4. Table liste_entreprise (pour verification dans pgAdmin)
ent_df = pd.DataFrame({"msisdn": ent_nums, "cle8": [cle(v) for v in ent_nums]})
with engine.begin() as conn:
    conn.execute(text("DROP TABLE IF EXISTS liste_entreprise CASCADE"))
ent_df.to_sql("liste_entreprise", engine, if_exists="replace", index=False)
print(f"\n[3] Table 'liste_entreprise' creee ({len(ent_df)} numeros) - visible dans pgAdmin")

# 5. Sauvegarde JSON
res = {
    "entreprise_total": len(ent_set),
    "modele_detecte": len(fresh_keys),
    "en_commun": len(vp),
    "manques": len(fn),
    "en_plus": len(fp),
    "precision": round(precision / 100, 4),
    "recall": round(recall / 100, 4),
}
with open("../data/comparaison_entreprise.json", "w") as f:
    json.dump(res, f, indent=2)
print("[4] Resultat sauvegarde : data/comparaison_entreprise.json")
print("\nTermine !")
