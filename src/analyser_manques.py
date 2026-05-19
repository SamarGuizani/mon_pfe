"""
OPTION A - Analyse : POURQUOI le modele rate 101 numeros de l'entreprise.

On regarde le profil (features) des numeros entreprise :
  - ceux que le modele a ATTRAPES (caught)
  - ceux que le modele a RATES (missed)
Et on compare, pour comprendre la difference.

Requetes legeres seulement (les 207 numeros, pas les 4M). Ne modifie rien.
"""
import re
import pandas as pd
from db_connection import get_engine

FICHIER = "/mnt/c/Users/USER/OneDrive/Desktop/ttdata.xlsx"


def cle(x):
    s = str(x).strip()
    if s.endswith(".0"):
        s = s[:-2]
    d = re.sub(r"\D", "", s)
    return d[-8:] if len(d) >= 8 else d


print("=" * 64)
print("  OPTION A - Pourquoi le modele rate 101 numeros ?")
print("=" * 64)

# 1. Les 207 numeros entreprise
ent = pd.read_excel(FICHIER, header=None)
ent_nums = [re.sub(r"\D", "", str(v).split(".")[0]) for v in ent[0].tolist()]
ent_keys = set(cle(v) for v in ent_nums)

engine = get_engine()

# 2. Detections du modele
fresh = pd.read_sql("SELECT msisdn FROM liste_noire_fresh", engine)
detected = set(cle(v) for v in fresh["msisdn"])
caught = ent_keys & detected      # attrapes
missed = ent_keys - detected      # rates
print(f"\nEntreprise : {len(ent_keys)} numeros | Attrapes : {len(caught)} | Rates : {len(missed)}")

# 3. Features des 207 numeros entreprise
candidats = set()
for n in ent_nums:
    candidats.add("+" + n)
    candidats.add(n)
liste_sql = ",".join("'" + c + "'" for c in candidats)
feat = pd.read_sql(f"SELECT * FROM features_msisdn_fresh WHERE msisdn IN ({liste_sql})", engine)
for c in feat.columns:
    if c != "msisdn":
        feat[c] = pd.to_numeric(feat[c], errors="coerce").fillna(0)
feat["cle"] = feat["msisdn"].apply(cle)
present = set(feat["cle"])

# 4. Numeros absents des donnees fresh (le modele ne pouvait PAS les voir)
absents = ent_keys - present
missed_absent = missed & absents
missed_present = missed - absents
print(f"\n--- RAISON 1 : numeros absents des donnees fresh ---")
print(f"  {len(absents)} numeros entreprise n'ont AUCUNE activite 'sortante' dans le CDR fresh")
print(f"  -> dont {len(missed_absent)} parmi les rates : le modele ne pouvait PAS les detecter")

# 5. Profil des rates PRESENTS vs des attrapes
feat["statut"] = feat["cle"].apply(lambda k: "attrape" if k in caught else "rate")
cols = ["appels_sortants", "variance_sortants", "distinct_imei",
        "location_count", "active_hours", "nb_jours_actifs", "duree_sortants"]

print(f"\n--- RAISON 2 : profil des numeros (moyennes) ---")
print(f"  {'feature':<22}{'ATTRAPES':>14}{'RATES (presents)':>20}")
g = feat.groupby("statut")
for c in cols:
    a = g[c].mean().get("attrape", 0)
    r = g[c].mean().get("rate", 0)
    print(f"  {c:<22}{a:>14.1f}{r:>20.1f}")

# 6. Combien des rates-presents passeraient la regle SIM Box
mp = feat[(feat["statut"] == "rate")]
regle = (mp["appels_sortants"] >= 15) & (
    (mp["variance_sortants"] >= 85) | (mp["distinct_imei"] >= 3) | (mp["location_count"] <= 3))
print(f"\n--- RAISON 3 : la regle SIM Box ---")
print(f"  Numeros rates presents dans le CDR fresh : {len(mp)}")
print(f"  Parmi eux, peu d'appels sortants (<15)   : {int((mp['appels_sortants'] < 15).sum())}")
print(f"  Qui passeraient quand meme la regle      : {int(regle.sum())}")

print("\nTermine !")
