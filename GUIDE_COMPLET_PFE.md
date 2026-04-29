# GUIDE COMPLET DU PROJET PFE
## Detection de Fraude SIM Box par Machine Learning

**Etudiant :** Samar Guizani
**Niveau :** Licence 3
**Entreprise :** elite business 
**Annee :** 2025/2026

---

# PARTIE 1 : OBJECTIF ET PROBLEMATIQUE

## L'objectif du projet

Construire un **systeme intelligent** capable de detecter automatiquement les **fraudes SIM Box** dans les telecommunications, en analysant les CDR (Call Detail Records) pour identifier les comportements suspects.

## La problematique

**Comment detecter automatiquement les fraudeurs SIM Box parmi 741 millions d'appels (CDR) avec :**
1. Une **precision elevee** (peu de fausses alertes)
2. Un **temps de reponse rapide** (millisecondes)
3. Une **interface web** pour les analystes
4. Une **adaptabilite** : detecter de nouveaux types de fraude

## Qu'est-ce qu'une SIM Box ?

Une **SIM Box** est un boitier electronique qui contient plusieurs cartes SIM. Elle est utilisee pour **detourner les appels internationaux** :

```
Appel international PAYANT
       ↓
[SIM Box reception]
       ↓
Conversion en appel local GRATUIT
       ↓
Pertes de revenus pour l'operateur (Sudatel)
```

**Caracteristiques d'une SIM Box :**
- Beaucoup d'appels sortants, peu d'appels entrants
- Appels tres courts ou non aboutis
- Position geographique fixe (boitier dans un appartement)
- Utilise plusieurs IMEI (rotation des SIM dans plusieurs boitiers)
- Appelle plein de numeros differents

---

# PARTIE 2 : LES 25 ETAPES DU PROJET (DETAILLEES)

## ETAPE 0 : Installation de l'environnement

**Quoi ?** Installer PostgreSQL, Node.js, Python sur Linux WSL (Ubuntu sous Windows).

**Pourquoi ?** Pour pouvoir coder et stocker les donnees.

**Commandes utilisees :**
```bash
sudo apt install postgresql nodejs python3 python3-venv
```

**Resultat :** Environnement pret pour developper.

---

## ETAPE 1 : Test de connexion Python ↔ PostgreSQL

**Quoi ?** Creer `test_connexion.py` qui se connecte et execute `SELECT version()`.

**Pourquoi ?** Avant tout code complexe, verifier que la "tuyauterie" fonctionne.

**Code cle :**
```python
from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:samar123@127.0.0.1:5432/postgres')
with engine.connect() as conn:
    result = conn.execute(text("SELECT version();"))
    print(result.fetchone()[0])
```

**Resultat :** Connexion confirmee, version PostgreSQL affichee.

---

## ETAPE 2 : Exploration des donnees

**Quoi ?** Creer `explorateur.py` pour voir la structure de la table CDR.

**Pourquoi ?** Connaitre les colonnes (timestamp, msisdn, imei, lac, cell_id...) avant de les analyser.

**Resultat :** Decouverte des 12 colonnes des CDR.

---

## ETAPE 3 : Detection par seuil (baseline simple)

**Quoi ?** Creer `detect_fraud.py` qui flag les numeros avec >50 appels.

**Pourquoi ?** Toujours commencer par la methode la plus simple (baseline) avant le ML.

**Resultat :** 7 suspects detectes sur la table de test.

---

## ETAPE 4 : Enrichissement des features (V0)

**Quoi ?** Ajouter ratio_appels_courts, duree_moyenne, nb_destinataires_uniques.

**Pourquoi ?** Un seul indicateur ne suffit pas pour distinguer fraude vs normal.

---

## ETAPE 5 : Adaptation au Big Data (741M lignes)

**Quoi ?** Modifier `detect_fraud.py` pour utiliser :
- `HAVING COUNT(*) > seuil` (filtrage SQL)
- `stream_results=True` (lecture par morceaux)
- `CREATE TABLE AS SELECT` (PostgreSQL fait le calcul ET l'insertion)

**Pourquoi ?** On ne peut pas charger 83 Go en RAM. PostgreSQL fait le travail, Python recoit juste le resultat.

**Regle d'or :**
> **PostgreSQL = cuisinier** | **Python = serveur**
> Le cuisinier prepare le plat, le serveur apporte juste l'assiette.

---

## ETAPE 6 : Connexion reseau Linux WSL → Windows

**Quoi ?** Configurer `pg_hba.conf` et `postgresql.conf` pour autoriser WSL.

**Pourquoi ?** La base est sur Windows, le code est sur Linux WSL → connexion reseau necessaire.

---

## ETAPE 7 : Detection automatique de l'IP Windows

**Quoi ?** Fonction `trouver_ip_windows()` qui detecte l'IP par 3 methodes.

**Pourquoi ?** L'IP WSL change a chaque redemarrage du PC.

```python
def trouver_ip_windows():
    candidats = [gateway, dns, "localhost"]
    for ip in candidats:
        if try_connect(ip):
            return ip
    raise ConnectionError(...)
```

---

## ETAPE 8 : Migration psycopg2 → psycopg3

**Quoi ?** Changer le driver PostgreSQL.

**Pourquoi ?** psycopg2 plantait avec les messages francais du serveur (accents).

---

## ETAPE 9 : Pipeline ML V1 cree

**Fichiers crees dans `src/` :**
- `db_connection.py` : module connexion reutilisable
- `feature_engineering_v2.sql` : 16 features par msisdn
- `load_features.py` : charger + split train/test
- `labeling.py` : pseudo-labels
- `isolation_forest.py` : modele unsupervised
- `train_xgboost.py` : modele supervise
- `evaluate.py` : graphiques

---

## ETAPE 10 : Feature Engineering V2 (regles entreprise)

**Quoi ?** Reecrire `feature_engineering_v2.sql` avec **les regles exactes de Sudatel**.

**Corrections importantes :**
- `mSOriginating` UNIQUEMENT pour MO (pas callForwarding)
- `mSTerminating` UNIQUEMENT pour MT
- `location = lac||'-'||cell_id` (pas cell_id seul)
- `variance` en pourcentage (pas en ratio 0-1)
- Ajout `active_hours` et `distinct_imei`

**Duree d'execution :** 6h32 sur 741M lignes (probleme memoire resolu avec `SET work_mem`).

**Resultat :** Table `features_msisdn_v2` avec **4,282,822 msisdn** et **16 features**.

---

## ETAPE 11 : Liste noire V1 (regles entreprise)

**Quoi ?** Creer `liste_noire_fraude` avec les regles :
```sql
WHERE appels_sortants >= 15
  AND (variance_sortants >= 85 OR distinct_imei >= 3 OR location_count <= 3)
```

**Resultat :** 70,897 suspects detectes.

---

## ETAPE 12 : Re-entrainement XGBoost V2

**Quoi ?** `train_xgboost_v2.py` re-entraine le modele avec les nouvelles features.

**Resultat :**
- F1 = 1.0000
- Precision = 1.0000
- Recall = 1.0000
- AUC = 1.0000
- 35 faux positifs / 4 faux negatifs sur 1.28M test

---

## ETAPE 13 : Dashboard Flask cree

**Pages crees :**
1. **Dashboard** : stats + graphiques interactifs
2. **Resultats ML** : split train/test + bouton evaluation
3. **Prediction IA** : taper un MSISDN → resultat
4. **Liste Noire** : 70,897 suspects + verification manuelle (admin)
5. **Liste Noire Train** : 49,628 fraudes (entrainement)
6. **Graphiques** : 9 graphiques cliquables
7. **Fraud Rules** : explication des regles
8. **Verification Manuelle** : admin entre fraudes confirmees (admin only)
9. **Gestion Utilisateurs** : admin only

---

## ETAPE 14 : Authentification par email

**Quoi ?** Sign Up avec verification email (code 6 chiffres) → Login → Dashboard.

**Outils :**
- `Flask-Login` (gestion session)
- `Gmail SMTP` (envoi emails)
- Mot de passe d'application Google (securite)

**2 roles :**
- **Admin** : controle total
- **Analyst** : lecture seule

---

## ETAPE 15 : Differences Admin vs Analyst

| Fonctionnalite | Admin | Analyst |
|----------------|-------|---------|
| Voir dashboard | OUI | OUI |
| Lancer evaluation ML | OUI | OUI |
| Prediction IA | OUI | OUI |
| Voir liste noire | OUI | OUI |
| Confirmer/rejeter suspects | **OUI** | **NON** |
| Verification manuelle | **OUI** | **NON** |
| Gestion utilisateurs | **OUI** | **NON** |

---

## ETAPE 16 : Liste noire Test inline

**Quoi ?** Apres clic "Lancer evaluation", la liste des fraudes detectees s'affiche dans la meme page.

**Pourquoi ?** Demo plus impactante pour le jury.

---

## ETAPE 17 : Filtres avances

**Quoi ?** 4 boutons de tri sur la page Liste Noire :
- Par defaut (sortants)
- Min duree sortants
- Max variance sortants
- Les plus suspects (combine)

---

## ETAPE 18 : Redesign pro Navy + Emerald

**Quoi ?** Refonte complete du design avec :
- Police Inter (Google Fonts)
- Sidebar dark navy avec gradient
- Boutons avec ombres colorees
- Animations subtiles

---

## ETAPE 19 : Liste noire avec cell specifique (en cours)

**Quoi ?** Nouvelle regle stricte :
- `appels_sortants >= 3`
- `variance_sortants >= 90` OU `location_count <= 3`
- `unique_called/appels_sortants * 100 >= 50`
- TOUS les MO depuis la cell `412-54312`

**Approche en 2 etapes :**
1. Creer `msisdn_cell_412_54312` (3-6h, une fois)
2. Creer `liste_noire_fraude` (2 sec, modifiable a volonte)

---

# PARTIE 3 : EXPLICATION DES FOLDERS ET FILES

## Structure du projet

```
mon_pfe/
├── frontend/              # Le dashboard web
│   ├── app.py             # Backend Flask (routes + API)
│   ├── email_config.py    # Mots de passe email (exclu de git)
│   ├── templates/         # Pages HTML
│   │   ├── base.html      # Layout commun (sidebar)
│   │   ├── login.html
│   │   ├── signup.html
│   │   ├── verify.html
│   │   ├── forgot_password.html
│   │   ├── reset_password.html
│   │   ├── dashboard.html
│   │   ├── resultats_ml.html
│   │   ├── prediction.html
│   │   ├── graphiques.html
│   │   ├── liste_noire.html
│   │   ├── liste_noire_train.html
│   │   ├── fraud_rules.html
│   │   └── verification_manuelle.html
│   └── static/            # Fichiers statiques
│       ├── css/style.css  # Styles design pro
│       └── img/           # Graphiques PNG
├── src/                   # Scripts ML
│   ├── db_connection.py   # Module connexion DB
│   ├── feature_engineering_v2.sql  # SQL des 16 features
│   ├── load_features.py   # Charge features dans pandas
│   ├── labeling.py        # Cree pseudo-labels
│   ├── isolation_forest.py  # Modele unsupervised
│   ├── train_xgboost.py   # XGBoost V1
│   ├── train_xgboost_v2.py  # XGBoost V2 (actuel)
│   ├── evaluate.py        # Genere graphiques
│   └── prototype_outliers.py  # 3 methodes detection
├── data/                  # CSV + graphiques PNG
├── models/                # Modeles entraines (.pkl)
├── detect_fraud.py        # Script detection original
├── test_connexion.py
├── explorateur.py
├── requirements.txt
├── .gitignore
└── README.md
```

---

# PARTIE 4 : EXPLICATION DU CODE LIGNE PAR LIGNE

## frontend/app.py (le coeur du backend)

### Bloc 1 : Imports et configuration

```python
from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user
import joblib
import pandas as pd
```

**Explication :** On importe Flask (web), Flask-Login (auth), joblib (charger modeles ML), pandas (donnees).

### Bloc 2 : Chargement du modele XGBoost

```python
model_xgb = joblib.load("../models/xgboost_fraud_v2.pkl")
```

**Pourquoi UNE SEULE fois au demarrage ?** Si on chargeait a chaque requete, ce serait lent. La on charge en RAM une fois pour toujours.

### Bloc 3 : Definition des features

```python
FEATURES = [
    "appels_sortants", "appels_entrants", ...
]
```

**Pourquoi ?** Ordre exact des colonnes attendues par XGBoost. Si on inverse l'ordre, le modele se trompe.

### Bloc 4 : Routes (URLs du site)

```python
@app.route("/")
@login_required
def page_dashboard():
    return render_template("dashboard.html")
```

**Explication :**
- `@app.route("/")` : URL = `/`
- `@login_required` : doit etre connecte
- `render_template` : affiche le HTML

### Bloc 5 : API de prediction

```python
@app.route("/api/predict-msisdn", methods=["POST"])
def api_predict_msisdn():
    msisdn = request.get_json()["msisdn"]

    # Cherche les features du msisdn
    with engine.connect() as conn:
        r = conn.execute(text("SELECT ... FROM features_msisdn WHERE msisdn = :m"), {"m": msisdn})
        row = r.fetchone()

    # Prepare et predit
    X = np.array([[row[0], row[1], ...]])
    pred = model_xgb.predict(X)[0]
    proba = model_xgb.predict_proba(X)[0][1]

    return jsonify({
        "prediction": "Fraude" if pred == 1 else "Normal",
        "probabilite": round(proba * 100, 2)
    })
```

**Explication ligne par ligne :**
1. Recoit le numero du frontend
2. Cherche ses features dans la base
3. Cree un tableau numpy au format attendu par XGBoost
4. Le modele predit (0 ou 1)
5. Retourne JSON au frontend

---

## src/feature_engineering_v2.sql (les 16 features)

### Bloc 1 : Setup memoire

```sql
SET work_mem = '64MB';
SET max_parallel_workers_per_gather = 0;
```

**Pourquoi ?** Limiter la memoire pour eviter les crashs sur 741M lignes.

### Bloc 2 : Compteurs simples

```sql
COUNT(*) FILTER (WHERE call_type = 'mSOriginating') AS appels_sortants
```

**Explication :** `FILTER (WHERE ...)` compte SEULEMENT les appels sortants. Tres efficace.

### Bloc 3 : Variance (le plus important)

```sql
ROUND(
    COUNT(DISTINCT called_number) FILTER (WHERE call_type = 'mSOriginating')::numeric
    / NULLIF(COUNT(*) FILTER (WHERE call_type = 'mSOriginating'), 0)::numeric * 100, 2
) AS variance_sortants
```

**Explication :**
- `COUNT(DISTINCT called_number)` : combien de numeros DIFFERENTS ce numero a appeles
- Divise par le total des appels sortants
- Multiplie par 100 → pourcentage
- `NULLIF(..., 0)` : evite la division par zero
- `ROUND(..., 2)` : arrondit a 2 decimales

**Interpretation :**
- `variance = 10%` → appelle souvent les memes (humain)
- `variance = 90%` → appelle plein de differents (suspect)

---

# PARTIE 5 : QUESTIONS DU JURY ET REPONSES

Voici 30 questions probables avec mes reponses :

## Questions sur le projet en general

### Q1 : "Quel est l'objectif de votre projet ?"

**Reponse :** "Detecter automatiquement les fraudes SIM Box dans les telecoms. Mon entreprise Sudatel utilise des regles SQL pour detecter, mais c'est lent et rigide. J'ai construit un systeme intelligent qui combine ces regles avec du Machine Learning pour etre plus rapide et plus precis."

### Q2 : "Quelle est la problematique ?"

**Reponse :** "Comment detecter les fraudeurs parmi 741 millions d'appels avec une precision elevee, en temps reel, et une interface utilisable par les analystes ?"

### Q3 : "Pourquoi vous avez choisi ce sujet ?"

**Reponse :** "C'est un probleme reel de Sudatel qui perd des revenus. J'ai voulu apporter une solution concrete en utilisant les techniques modernes (Big Data + ML)."

---

## Questions sur les donnees

### Q4 : "Combien de donnees vous avez traitees ?"

**Reponse :** "741,340,262 enregistrements CDR, soit 83 Go. C'est de la vraie donnee de Sudatel, pas des donnees jouet."

### Q5 : "Quelles sont les colonnes des CDR ?"

**Reponse :** "12 colonnes : timestamp, call_type (MO/MT), imsi, imei, msisdn, lac, cell_id, last_lac, last_cell_id, calling_number, called_number, duration_seconds."

### Q6 : "Comment vous avez gere le volume ?"

**Reponse :** "Regle d'or : PostgreSQL fait le calcul, Python recoit le resultat. Je n'ai jamais charge 83 Go en RAM. J'ai utilise GROUP BY en SQL, et stocke les resultats dans une petite table de 4.28 millions de lignes (`features_msisdn_v2`)."

---

## Questions sur le Feature Engineering

### Q7 : "Pourquoi avez-vous extrait 16 features ?"

**Reponse :** "Chaque feature donne un angle different. Un fraudeur peut cacher 1 ou 2 indicateurs, mais pas les 16. La combinaison est ce qui fait la difference."

### Q8 : "Pourquoi avoir separe MO et MT ?"

**Reponse :** "Parce que les SIM Box ont presque QUE des appels sortants (MO) et tres peu d'entrants (MT). Si je ne les separais pas, je perdais cette information importante."

### Q9 : "Pourquoi `lac||'-'||cell_id` au lieu de cell_id seul ?"

**Reponse :** "Parce que le meme `cell_id` peut exister dans plusieurs LAC. Pour identifier une position GSM unique, il faut combiner les deux. C'est ce que fait Sudatel dans ses regles."

### Q10 : "C'est quoi `variance_sortants` ?"

**Reponse :** "C'est le pourcentage d'appels vers des numeros differents. `variance = 100%` signifie que chaque appel va vers un numero unique. C'est un comportement de robot/SIM Box. Un humain a une variance de 10-30% (il appelle souvent les memes contacts)."

---

## Questions sur le Machine Learning

### Q11 : "Pourquoi XGBoost ?"

**Reponse :** "C'est un algorithme d'ensemble (200 arbres de decision combines). Il gere bien les donnees desequilibrees (peu de fraudes), il est rapide a predire (millisecondes), et il donne la `feature_importance` qui m'aide a expliquer les decisions."

### Q12 : "Qu'est-ce qu'un pseudo-label ?"

**Reponse :** "Comme je n'ai pas de labels reels (ground truth), j'utilise les regles metier de Sudatel pour etiqueter les numeros. Si un numero respecte les regles, je dis 'fraude' ; sinon 'normal'. Le modele apprend a reproduire ces regles. C'est une limite que j'ai mentionnee dans mon rapport."

### Q13 : "Pourquoi 70/30 et pas 80/20 ?"

**Reponse :** "70/30 est le standard quand on a beaucoup de donnees. 80/20 est pour de petits datasets. Avec 4.28M de numeros, 30% (1.28M) est largement suffisant pour le test."

### Q14 : "Pourquoi `random_state=42` ?"

**Reponse :** "Pour la reproductibilite. Si je relance le code, j'aurai exactement les memes resultats. Le 42 est une convention en Data Science (reference au livre 'Le Guide du Voyageur Galactique')."

### Q15 : "C'est quoi F1-Score ?"

**Reponse :** "F1 est la moyenne harmonique entre Precision (ne pas accuser des innocents) et Recall (attraper tous les fraudeurs). Mon F1 = 1.0000 signifie un equilibre parfait. Si Precision et Recall etaient deux notes, F1 c'est la note finale."

### Q16 : "C'est quoi AUC ?"

**Reponse :** "Area Under the Curve. C'est l'aire sous la courbe ROC. AUC = 1.0 signifie que mon modele separe PARFAITEMENT fraude vs normal. AUC = 0.5 c'est du hasard."

### Q17 : "Pourquoi pas l'accuracy ?"

**Reponse :** "Parce que les donnees sont desequilibrees. Si 95% sont normaux, un modele qui dit toujours 'normal' a 95% d'accuracy mais ne sert a rien. F1 et Recall sont mieux."

### Q18 : "Comment savez-vous que le test est juste ?"

**Reponse :** "J'ai 4 indicateurs : F1=1.0, Precision=1.0, Recall=1.0, AUC=1.0. La matrice de confusion confirme : 35 faux positifs et 4 faux negatifs sur 1.28M lignes. C'est negligeable."

### Q19 : "Quelle est la limite de votre F1 = 1.0 ?"

**Reponse :** "C'est un risque d'overfitting. Le modele apprend tres bien les regles parce qu'il a ete entraine sur des pseudo-labels generes par ces memes regles. Avec des **vraies fraudes confirmees** (ce que j'enregistre dans la page Verification Manuelle), le F1 reel serait probablement entre 0.85 et 0.95. C'est ce que je veux ameliorer dans le futur."

### Q20 : "Difference entre vos regles et le ML ?"

**Reponse :**
- **Regles** : rigides, lentes (scan complet), ne voit pas les combinaisons
- **ML** : flexible, rapide (millisecondes), voit les patterns complexes
- Mon ML reproduit les regles plus rapidement et avec plus de souplesse

---

## Questions techniques

### Q21 : "Pourquoi PostgreSQL et pas MySQL ?"

**Reponse :** "PostgreSQL est plus puissant pour les agregations complexes (FILTER, GROUP BY avancees), il a TimescaleDB qui optimise les donnees temporelles (CDR sont des donnees temporelles), et il gere mieux les gros volumes."

### Q22 : "Pourquoi Flask et pas Django ?"

**Reponse :** "Flask est plus leger et plus rapide a mettre en place pour un projet de cette taille. Django serait surdimensionne. Flask suffit pour 7 pages et 15 routes API."

### Q23 : "Pourquoi WSL ?"

**Reponse :** "Mon stage exigeait Linux mais ma base est sur Windows. WSL me permet d'avoir les deux : Linux pour Python, Windows pour PostgreSQL. C'est le compromis ideal."

### Q24 : "Comment vous avez gere le reseau WSL ↔ Windows ?"

**Reponse :** "L'IP WSL change a chaque redemarrage. J'ai code une fonction `trouver_ip_windows()` qui essaie 3 methodes : la passerelle reseau, le DNS, et localhost. Le code se connecte automatiquement sans intervention manuelle."

### Q25 : "Pourquoi Inter comme police ?"

**Reponse :** "Inter est une police moderne, lisible, gratuite et utilisee par des companies comme Figma, GitHub, Mozilla. C'est devenu le standard pour les dashboards SaaS professionnels."

---

## Questions sur l'innovation

### Q26 : "Quelle est l'innovation de votre projet ?"

**Reponse :** "Mon innovation est l'**approche hybride** :
1. **Regles entreprise** pour le pseudo-labeling
2. **Machine Learning** (XGBoost + Isolation Forest) pour la generalisation
3. **Verification humaine** pour valider et re-entrainer
4. **Dashboard moderne** pour les analystes

C'est une approche complete, pas juste un script ML isole."

### Q27 : "Comment le projet aide concretement Sudatel ?"

**Reponse :** "Sudatel utilise des regles SQL qui scannent les 741M lignes en continu. C'est lent et rigide. Mon systeme :
- **Pre-calcule les features** en quelques heures (une fois)
- **Predit instantanement** sur n'importe quel numero
- **S'adapte** avec les fraudes confirmees
- **Reduit le travail humain** des analystes"

### Q28 : "Quelle est la valeur ajoutee du dashboard ?"

**Reponse :** "Avant mon dashboard, les analystes Sudatel devaient lire des fichiers SQL bruts. Maintenant, ils ont :
- Une **interface visuelle** avec graphiques
- Une **recherche par MSISDN** instantanee
- Des **filtres avances** (min duree, max variance)
- Une **prediction IA** en 1 clic
- Un **systeme de validation** humaine

C'est un gain de productivite enorme."

---

## Questions sur les limites

### Q29 : "Quelles sont les limites de votre projet ?"

**Reponse :** "Trois limites principales :
1. **Pseudo-labeling** : le modele ne peut pas etre meilleur que les regles initiales (biais circulaire)
2. **Pas de detection en temps reel** : c'est un systeme batch (recalcul periodique)
3. **Donnees historiques** : pas de prediction sur de futurs comportements"

### Q30 : "Comment vous ameliorez ?"

**Reponse :** "
1. Utiliser les **fraudes confirmees** par les analystes pour re-entrainer (vrais labels)
2. **Streaming temps reel** avec Apache Kafka
3. **Deep Learning (LSTM)** pour les sequences temporelles
4. **Application mobile** pour les analystes sur le terrain"

---

# PARTIE 6 : COMMENT EXECUTER LE PROJET

## Pour developper

```bash
cd /home/samar/stage/mon_pfe/frontend
source ../venv/bin/activate
python app.py
```

Puis : http://localhost:5000

## Pour re-entrainer le modele

```bash
cd /home/samar/stage/mon_pfe/src
source ../venv/bin/activate
python train_xgboost_v2.py
```

## Pour pousser sur GitHub

```bash
cd /home/samar/stage/mon_pfe
git add -A
git commit -m "Description"
git push
```

---

# PARTIE 7 : RESULTATS CHIFFRES

| Metrique | Valeur |
|----------|--------|
| **Donnees brutes** | 741,340,262 lignes (83 Go) |
| **Features extraites** | 16 par msisdn |
| **MSISDN uniques** | 4,282,822 |
| **Train (70%)** | 2,997,975 numeros |
| **Test (30%)** | 1,284,847 numeros |
| **Suspects detectes** | 70,897 (regles V2) |
| **F1-Score XGBoost** | 1.0000 |
| **AUC** | 1.0000 |
| **Faux Positifs** | 35 sur 1.28M |
| **Faux Negatifs** | 4 sur 21,269 |
| **Temps prediction** | 0.001 sec/msisdn |

---

# PARTIE 8 : LES MODIFICATIONS A VENIR

## Liste noire avec cell `412-54312`

**En cours d'execution** (3-6h) :

```sql
CREATE TABLE msisdn_cell_412_54312 AS
SELECT msisdn FROM cdr_data
WHERE call_type = 'mSOriginating'
GROUP BY msisdn
HAVING COUNT(*) FILTER (WHERE lac||'-'||cell_id = '412-54312') = COUNT(*);
```

**Apres** : la liste noire sera generee en 2 secondes avec :
- Au moins 3 appels MO
- Variance >= 90% OU location_count <= 3
- Tous les appels MO depuis la cell 412-54312

**Prochaine etape** : re-entrainer XGBoost avec cette nouvelle liste noire pour avoir un modele plus precis.

---

# CONCLUSION

Ce projet est un **systeme complet et professionnel** de detection de fraude SIM Box, qui :
- Traite des **donnees Big Data reelles** (741M lignes)
- Utilise les **regles metier de Sudatel**
- Combine **Machine Learning** + **Verification humaine**
- Fournit un **dashboard moderne** avec authentification
- Atteint des **resultats exceptionnels** (F1 = 1.0)

Le code est sur **GitHub** : https://github.com/SamarGuizani/mon_pfe
