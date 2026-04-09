# Historique du Projet PFE - Detection de Fraude SIM Box

## Informations Projet
- **Etudiant** : Samar Guizani
- **Niveau** : Licence 3 (PFE)
- **Sujet** : Detection de fraude SIM Box dans les telecoms
- **Donnees** : 741,340,262 lignes CDR (83 Go)
- **GitHub** : https://github.com/SamarGuizani/mon_pfe

---

## Etape 0 : Installation de l'environnement
- Installe PostgreSQL 16, Node.js 18, Python 3.12 sur Linux WSL (Ubuntu)
- Cree un environnement virtuel Python (venv)
- Installe les dependances : pandas, sqlalchemy, psycopg2, scikit-learn, xgboost, matplotlib, seaborn

## Etape 1 : Test de connexion Python → PostgreSQL
- Cree `test_connexion.py` pour verifier que Python peut parler a PostgreSQL
- Corrige les erreurs de compatibilite pandas/SQLAlchemy 2.x (utiliser `text()` et `engine.connect()`)
- Connexion reussie

## Etape 2 : Exploration des donnees
- Cree `explorateur.py` pour voir un echantillon de la table CDR
- Colonnes trouvees : timestamp, call_type, imsi, imei, msisdn, lac, cell_id, last_lac, last_cell_id, calling_number, called_number, duration_seconds

## Etape 3 : Detection par regles (seuil) sur cdr_test
- Cree `detect_fraud.py` : compte les appels par msisdn, flag ceux avec >50 appels
- 7 suspects detectes sur la petite table `cdr_test`
- Sauvegarde dans `liste_noire_fraude` avec `engine.begin()` pour auto-commit

## Etape 4 : Enrichissement des features
- Ajoute 3 colonnes : ratio_appels_courts, duree_moyenne, nb_destinataires_uniques
- Resultat : 7 suspects avec 6 features au lieu de 3
- Observations : la plupart des suspects ont duration=0 (appels non aboutis)

## Etape 5 : Adaptation au Big Data (741M lignes)
- Modifie `detect_fraud.py` pour utiliser :
  - `HAVING COUNT(*) > seuil` (filtrage SQL, pas Python)
  - `stream_results=True` (lecture par morceaux)
  - `CREATE TABLE AS SELECT` (PostgreSQL fait le calcul + insertion)
- Regle d'or : PostgreSQL fait le calcul, Python recoit juste le resultat

## Etape 6 : Connexion reseau Linux WSL → Windows
- La base de 83 Go est sur Windows (192.168.0.80), Python tourne sur Linux WSL
- Configure `postgresql.conf` : `listen_addresses = '*'`
- Configure `pg_hba.conf` : `host all all 172.29.0.0/16 scram-sha-256`
- Ouvre le pare-feu Windows sur le port 5432

## Etape 7 : Detection automatique de l'IP Windows
- Cree `trouver_ip_windows()` : detecte l'IP automatiquement (3 methodes)
  1. `ip route show default` (passerelle)
  2. `/etc/resolv.conf` (DNS WSL)
  3. `localhost` (fallback)
- L'IP WSL change a chaque redemarrage du PC

## Etape 8 : Migration psycopg2 → psycopg3
- psycopg2 plantait avec les messages en francais du serveur Windows (accents = erreur UTF-8)
- Installe `psycopg[binary]` (version 3)
- Mise a jour SQLAlchemy de 1.3 → 2.0
- Utilise `postgresql+psycopg://` comme driver

## Etape 9 : Feature Engineering V1 (12 features)
- Cree `src/feature_engineering.sql` : 12 features par msisdn
- Execute dans pgAdmin : **2h19** pour scanner 741M lignes
- Resultat : table `features_msisdn` avec **4,282,822 msisdn**
- Problemes rencontres : disque plein (libere 100 Go), compression TimescaleDB tuee

## Etape 10 : Pipeline Machine Learning
Scripts crees dans `src/` :
- `load_features.py` : charge features + split 70/30 train/test
- `labeling.py` : pseudo-labels (5 regles combinees, >=2 = fraude) → 24.8% fraude
- `isolation_forest.py` : detection unsupervised (5% anomalies)
- `train_xgboost.py` : classification supervisee → **F1 = 0.997, AUC = 1.0**
- `evaluate.py` : 5 graphiques (confusion matrix, ROC, precision-recall, feature importance, scores)
- `prototype_outliers.py` : 3 methodes (Z-Score, IQR, Isolation Forest) + vote consensus

## Etape 11 : Feature Engineering V2 (regles entreprise)
Features corrigees selon les vraies regles de l'entreprise :
- `appels_sortants` / `appels_entrants` (separes MO/MT)
- `duree_sortants` / `duree_entrants`
- `avg_duree_sortants` / `avg_duree_entrants`
- `variance_sortants` = distinct appeles / total MO * 100 (en %, seuil 85%)
- `variance_entrants` = distinct appelants / total MT * 100
- `location_count` = DISTINCT **lac||'-'||cell_id** (pas cell_id seul)
- `active_hours` = DISTINCT DATE_TRUNC('hour') (NOUVEAU)
- `distinct_imei` = COUNT(DISTINCT imei) (NOUVEAU)

Corrections appliquees :
- location = lac+cell_id combine (comme l'entreprise)
- variance en % (pas en ratio 0-1)
- ROUND avec ::numeric (pas ::FLOAT)

## Etape 12 : Liste Noire V2 (regles entreprise)
Regles appliquees :
```sql
WHERE appels_sortants >= 15
AND (variance_sortants >= 85 OR distinct_imei >= 3 OR location_count <= 3)
```
Resultat : **90,353 suspects** (au lieu de 986K avec les anciennes regles)

## Etape 13 : Dashboard Flask (3 pages initiales)
- Page 1 : Dashboard (stats + graphiques interactifs Chart.js)
- Page 2 : Graphiques (9 cartes cliquables, modal pour afficher l'image)
- Page 3 : Liste Noire (table paginee avec recherche)
- Theme sombre initial, navigation en haut

## Etape 14 : Authentification par email
- Sign Up : email + username + mot de passe + role (admin/analyst)
- Verification : code 6 chiffres envoye par email (Gmail SMTP)
- Sign In : email + mot de passe (verifie is_verified en base)
- Forgot Password : code de reinitialisation envoye par email
- Table `users` : id, email, username, password_hash, role, is_verified, verification_code, reset_code
- Table `login_history` : log de chaque action (signup, login, logout)
- Flask-Login pour la gestion de session
- `@login_required` sur toutes les pages

## Etape 15 : Page Resultats ML (train vs test)
- Affiche 70% train (bleu) vs 30% test (vert) cote a cote
- Bouton "Lancer l'evaluation" : le modele XGBoost predit sur les 30% EN DIRECT
- Affiche : F1, Precision, Recall, AUC + matrice de confusion HTML
- Explication simple : "comme un etudiant qui apprend (70%) puis passe l'examen (30%)"
- Explication de verification : comment lire F1, matrice de confusion

## Etape 16 : Page Prediction IA
- Champ de recherche : taper un MSISDN
- Le backend cherche les features dans `features_msisdn`
- XGBoost predit : FRAUDE (rouge) ou NORMAL (vert) + probabilite
- Affiche les 12 features avec couleurs (anormal en rouge si > 2 ecarts-types)
- Le modele est charge UNE FOIS au demarrage de Flask

## Etape 17 : Redesign complet du dashboard
- **Sidebar a gauche** (comme le systeme de l'entreprise dans les screenshots)
- **Couleurs jaune/blanc** au lieu du theme sombre
- 6 pages dans la sidebar : Dashboard, Resultats ML, Prediction IA, Liste Noire, Graphiques, Fraud Rules
- User info en bas de la sidebar (avatar, nom, badge role, deconnexion)

## Etape 18 : Page Fraud Rules
- Tableau des 11 features extraites avec formule SQL
- 6 cartes de regles de l'entreprise (Bypass General, SIM Box IMEI, Cell Location, Active Hours, Bypass Offnet, Regle combinee)
- Chaque carte : description, tags, code SQL
- Explication : comment le ML utilise ces regles (pseudo-labels → entrainement → test)

## Etape 19 : Push sur GitHub
- Repo : https://github.com/SamarGuizani/mon_pfe
- `email_config.py` exclu du repo (contient le mot de passe Gmail)
- 2 commits : initial + auth system + ML results + prediction

---

## Tables PostgreSQL

| Table | Lignes | Description |
|-------|--------|-------------|
| `cdr_data` | 741,340,262 | Donnees brutes CDR (hypertable TimescaleDB) |
| `features_msisdn` | 4,282,822 | Features V1 (12 features) |
| `features_msisdn_v2` | 4,282,822 | Features V2 corrigees (entreprise) |
| `liste_noire_fraude` | 90,353 | Suspects detectes (regles V2) |
| `users` | 2 | Comptes admin + analyst |
| `login_history` | - | Historique des connexions |

## Structure du Projet

```
mon_pfe/
├── frontend/
│   ├── app.py                    # Flask backend (routes + API)
│   ├── email_config.py           # Config Gmail (exclu de Git)
│   ├── templates/
│   │   ├── base.html             # Layout avec sidebar
│   │   ├── login.html            # Page connexion
│   │   ├── signup.html           # Page inscription
│   │   ├── verify.html           # Verification email
│   │   ├── forgot_password.html  # Mot de passe oublie
│   │   ├── reset_password.html   # Reinitialiser mdp
│   │   ├── dashboard.html        # Stats + graphiques
│   │   ├── resultats_ml.html     # Train vs Test + demo live
│   │   ├── prediction.html       # Prediction IA par MSISDN
│   │   ├── graphiques.html       # 9 graphiques cliquables
│   │   ├── liste_noire.html      # Table des suspects
│   │   └── fraud_rules.html      # Regles de l'entreprise
│   └── static/
│       ├── css/style.css         # Design jaune/blanc + sidebar
│       ├── js/dashboard.js       # JS (ancien, remplace par inline)
│       └── img/                  # 9 graphiques PNG
├── src/
│   ├── db_connection.py          # Module connexion reutilisable
│   ├── feature_engineering_v2.sql # SQL features (corrige entreprise)
│   ├── load_features.py          # Charge features + split 70/30
│   ├── labeling.py               # Pseudo-labels
│   ├── isolation_forest.py       # Modele unsupervised
│   ├── train_xgboost.py          # Modele supervise (F1=0.997)
│   ├── evaluate.py               # Graphiques pour le rapport
│   └── prototype_outliers.py     # 3 methodes + vote
├── data/                         # CSV + PNG (CSV exclus de Git)
├── models/                       # .pkl (XGBoost, Isolation Forest, Scaler)
├── detect_fraud.py               # Script original de detection
├── test_connexion.py             # Test connexion
├── explorateur.py                # Exploration donnees
├── requirements.txt              # Dependances Python
└── .gitignore                    # Exclusions Git
```

## Comptes par defaut
- **Admin** : samarguizani07@gmail.com (role: admin)
- **Analyst** : guizanisamarz@gmail.com (role: analyst)

## Ce qui reste a faire
- [ ] Feature 3 : Verification manuelle (confirmer/rejeter suspects dans la liste noire)
- [ ] Feature 5 : Upload dynamique (importer de nouvelles donnees CDR)
- [ ] Feature 6 : Notebook Google Colab (exige par le prof)
- [ ] Feature 7 : Page Methodologie (innovation pour le jury)
- [ ] Push final sur GitHub
