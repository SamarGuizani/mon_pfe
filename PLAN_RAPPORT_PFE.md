# PLAN DE RAPPORT DE PFE
## Detection de Fraude SIM Box par Machine Learning dans les Telecoms

**Etudiant :** Samar Guizani
**Niveau :** Licence 3
**Entreprise :** Sudatel
**Encadrant universitaire :** [Nom]
**Encadrant entreprise :** [Nom]
**Annee universitaire :** 2025/2026

---

## Page de garde (1 page)
## Remerciements (1 page)
## Sommaire (2 pages)
## Liste des figures (1 page)
## Liste des tableaux (1 page)
## Liste des abreviations (1 page)
- CDR, SIM Box, MSISDN, IMSI, IMEI, LAC, MO, MT, ML, XGBoost, AUC, ROC, F1, API, REST, WSL, SMTP

---

## Introduction Generale (3-4 pages)

- Contexte general : croissance du secteur telecom, augmentation des fraudes
- La fraude SIM Box : un probleme mondial qui coute des milliards aux operateurs
- Problematique : Comment detecter automatiquement les numeros fraudeurs parmi 741 millions d'enregistrements d'appels ?
- Objectif du PFE : concevoir et developper un systeme de detection de fraude SIM Box qui combine les regles metier de l'entreprise avec des algorithmes de Machine Learning, deploye dans un dashboard web interactif
- Methodologie adoptee : Feature Engineering sur Big Data → Apprentissage supervise et non-supervise → Deploiement web
- Annonce du plan du rapport (chapitre par chapitre)

---

## Chapitre 1 : Cadre General du Projet (12-15 pages)

### 1.1 Presentation de l'entreprise d'accueil (3-4 pages)
- Historique de Sudatel
- Domaine d'activite, services proposes
- Organigramme
- Departement d'accueil (equipe fraude / IT)
- Mon role dans l'entreprise pendant le stage

### 1.2 La fraude SIM Box dans les telecoms (4-5 pages)
- Definition de la SIM Box (schema explicatif detaille)
- Mecanisme de la fraude : appel international → passerelle SIM Box → appel local
- Types de fraude : bypass simple, bypass offnet, bypass avec IMEI rotatif
- Impact financier sur les operateurs (chiffres mondiaux et locaux)
- Impact sur la qualite de service
- Enjeux legaux et reglementaires

### 1.3 Etat de l'art et travaux existants (4-5 pages)
- Methodes traditionnelles (regles statiques, seuils)
- Methodes basees sur le Machine Learning (arbres de decision, SVM, Random Forest, XGBoost)
- Methodes basees sur le Deep Learning (reseaux de neurones, LSTM)
- Detection d'anomalies (Isolation Forest, DBSCAN, Autoencoders)
- Tableau comparatif des approches existantes
- Limites identifiees dans la litterature
- Positionnement de notre approche par rapport a l'existant

### 1.4 Cahier des charges (2-3 pages)
- Besoins fonctionnels : detection automatique, dashboard, prediction, authentification, verification manuelle
- Besoins non-fonctionnels : performance (741M lignes), securite (roles), utilisabilite
- Contraintes techniques : PostgreSQL/TimescaleDB sur Windows, Python sur Linux WSL, donnees reelles
- Planning previsionnel du stage (diagramme de Gantt)

---

## Chapitre 2 : Analyse et Conception (15-18 pages)

### 2.1 Analyse des besoins (3-4 pages)
- Identification des acteurs : Administrateur, Analyste Fraude
- Besoins de l'administrateur : gestion complete (configurer les regles, lancer l'evaluation ML, confirmer/rejeter les suspects, gerer les utilisateurs)
- Besoins de l'analyste : consultation et analyse (voir le dashboard, rechercher des numeros, faire des predictions, consulter la liste noire)
- Tableau detaille des droits d'acces par role

### 2.2 Diagramme de cas d'utilisation (3-4 pages)
- Diagramme Use Case global du systeme
- Use Case detaille : "Se connecter" (signup, verification email, login, mot de passe oublie)
- Use Case detaille : "Detecter une fraude" (prediction IA sur un MSISDN)
- Use Case detaille : "Verifier un suspect" (confirmer fraude / marquer faux positif)
- Use Case detaille : "Consulter les resultats ML" (lancer evaluation, voir metriques)
- Description textuelle de chaque cas d'utilisation

### 2.3 Diagrammes de sequence (3-4 pages)
- Sequence : Processus d'inscription et verification email
- Sequence : Prediction IA (utilisateur tape MSISDN → Flask → XGBoost → resultat)
- Sequence : Lancement de l'evaluation ML (admin clique → charge test set → XGBoost predit → affiche metriques)
- Sequence : Verification manuelle d'un suspect (admin confirme → update base → compteurs mis a jour)

### 2.4 Diagramme de classes (2-3 pages)
- Classes principales : User, CDR, FeatureMSISDN, ListeNoire, Verification, LoginHistory
- Attributs et methodes de chaque classe
- Relations : heritage, association, composition

### 2.5 Modele de donnees (3-4 pages)
- Modele Conceptuel de Donnees (MCD)
- Modele Logique de Donnees (MLD)
- Description de chaque table :
  - `cdr_data` : 741M lignes, 12 colonnes, hypertable TimescaleDB
  - `features_msisdn_v2` : 4.28M lignes, 18 colonnes (features calculees)
  - `liste_noire_fraude` : 90,353 lignes (suspects detectes)
  - `users` : comptes utilisateurs avec hash mot de passe
  - `verification_fraude` : statuts de verification humaine
  - `login_history` : journal des connexions
- Dictionnaire de donnees complet

### 2.6 Architecture technique du systeme (2-3 pages)
- Schema d'architecture 3-tiers (Navigateur → Flask → PostgreSQL)
- Architecture reseau : Linux WSL ↔ Windows (TCP/IP port 5432)
- Architecture du pipeline ML : PostgreSQL → Pandas → XGBoost → Flask → Navigateur
- Choix techniques justifies (pourquoi PostgreSQL, pourquoi Flask, pourquoi XGBoost)

---

## Chapitre 3 : Feature Engineering et Regles de Detection (12-15 pages)

### 3.1 Les donnees brutes CDR (3-4 pages)
- Source des donnees : systeme MSC de Sudatel
- Volume : 741,340,262 enregistrements, 83 Go
- Structure : timestamp, call_type, imsi, imei, msisdn, lac, cell_id, calling_number, called_number, duration_seconds
- Types d'appels : mSOriginating (MO), mSTerminating (MT), callForwarding, SMS
- Periode couverte par les donnees
- Statistiques descriptives (nombre de MSISDN uniques, duree moyenne, distribution des appels)
- Echantillon de donnees (tableau)

### 3.2 Processus de Feature Engineering (4-5 pages)
- Principe : transformer 741M lignes brutes en 4.28M lignes de features (GROUP BY msisdn)
- Tableau des 11 features extraites :

| # | Feature | Formule SQL | Justification metier |
|---|---------|------------|---------------------|
| 1 | appels_sortants | COUNT(*) FILTER (MO) | Volume d'activite sortante |
| 2 | appels_entrants | COUNT(*) FILTER (MT) | Volume d'activite entrante |
| 3 | duree_sortants | SUM(duration) FILTER (MO) | Duree totale des sortants |
| 4 | duree_entrants | SUM(duration) FILTER (MT) | Duree totale des entrants |
| 5 | avg_duree_sortants | AVG(duration) FILTER (MO) | Profil d'appel moyen |
| 6 | avg_duree_entrants | AVG(duration) FILTER (MT) | Profil d'appel moyen |
| 7 | variance_sortants | DISTINCT called / total MO * 100 | Diversite des appeles (85-100% = suspect) |
| 8 | variance_entrants | DISTINCT calling / total MT * 100 | Diversite des appelants |
| 9 | location_count | DISTINCT lac\|\|'-'\|\|cell_id | Mobilite geographique (<=3 = fixe = suspect) |
| 10 | active_hours | DISTINCT DATE_TRUNC('hour') | Heures d'activite (<=3 = burst = suspect) |
| 11 | distinct_imei | COUNT(DISTINCT imei) | Nombre d'appareils (>=3 = SIM Box) |

- Requete SQL complete commentee
- Temps d'execution : 3h11 sur 741M lignes
- Problemes rencontres : memoire epuisee, conversion ::numeric vs ::float

### 3.3 Regles de detection de l'entreprise (4-5 pages)
- Origine des regles : systeme de detection existant de Sudatel
- Description de chaque regle :
  - **Rule Bypass General** : variance >= 100%, duree MT = 0, appels MO >= 30
  - **Rule Bypass SIM Box (IMEI)** : IMEI distincts >= 3, appels MO >= 3
  - **Rule Cell Location** : locations <= 3, variance >= 85%, appels MO >= 15
  - **Rule Active Hours** : heures actives <= 3, variance >= 100%, appels MO >= 7
  - **Rule Bypass Offnet** : variance >= 95%, appels MT >= 15
  - **Rule combinee (Liste Noire)** : MO >= 15 AND (variance >= 85% OR IMEI >= 3 OR locations <= 3)
- Tableau comparatif des seuils par regle
- Resultat : 90,353 suspects detectes sur 4.28M MSISDN (2.1%)

### 3.4 Analyse exploratoire des features (2-3 pages)
- Distribution de chaque feature (histogrammes)
- Matrice de correlation entre les features
- Comparaison des profils : numeros normaux vs suspects
- Graphique : appels sortants vs entrants (suspects en rouge)
- Graphique : variance vs mobilite

---

## Chapitre 4 : Machine Learning (15-18 pages)

### 4.1 Strategie de labeling (3-4 pages)
- Probleme : absence de labels ground truth (on ne sait pas avec certitude qui est fraudeur)
- Solution adoptee : pseudo-labeling base sur les regles metier de l'entreprise
- Regles de labeling : un MSISDN est "fraude" si au moins 2 conditions sur 5 sont remplies
- Avantages : utilise l'expertise metier existante
- Limites : le modele ne peut pas etre meilleur que les regles (biais circulaire)
- Discussion : comment ameliorer avec des labels reels

### 4.2 Preparation des donnees (2-3 pages)
- Split train/test : 70% (2,997,975 MSISDN) / 30% (1,284,847 MSISDN)
- Justification du ratio 70/30 (standard en ML, compromis biais-variance)
- Seed aleatoire (random_state=42) pour reproductibilite
- Traitement des valeurs manquantes (fillna(0))
- Distribution des classes : 75.2% normal / 24.8% fraude
- Probleme de desequilibre des classes et solution (scale_pos_weight)

### 4.3 Modele XGBoost - Approche supervisee (4-5 pages)
- Presentation de XGBoost (eXtreme Gradient Boosting)
- Principe : ensemble d'arbres de decision entraines sequentiellement
- Avantages : performance elevee, gere le desequilibre, feature importance native
- Hyperparametres choisis :
  - n_estimators = 200 (nombre d'arbres)
  - max_depth = 6 (profondeur maximale)
  - learning_rate = 0.1 (taux d'apprentissage)
  - scale_pos_weight = ratio normal/fraude (gestion du desequilibre)
- Processus d'entrainement (schema)
- Temps d'entrainement : ~5 minutes sur 3M lignes

### 4.4 Modele Isolation Forest - Approche non-supervisee (3-4 pages)
- Principe : isoler les points anormaux (faciles a separer = suspects)
- Avantage : pas besoin de labels
- Parametre contamination = 0.05 (5% supposes fraudeurs)
- n_estimators = 200
- Resultat : 214,142 anomalies detectees (5%)
- Comparaison avec les pseudo-labels : overlap de 38,074

### 4.5 Detection d'outliers multi-methodes (2-3 pages)
- Methode Z-Score : seuil = 3 ecarts-types → 125,291 outliers (2.93%)
- Methode IQR : Q3 + 1.5*IQR → 636,831 outliers (14.87%)
- Methode Isolation Forest : → 214,142 outliers (5%)
- Vote consensus (>=2 methodes sur 3) : 216,249 suspects (5.05%)
- Avantage du consensus : reduit les faux positifs

### 4.6 Evaluation et resultats (4-5 pages)
- Pourquoi ne pas utiliser l'accuracy (90% accuracy = inutile si 90% normaux)
- Metriques utilisees : Precision, Recall, F1-Score, AUC
- Resultats XGBoost sur le test set (30%) :

| Metrique | Valeur | Interpretation |
|----------|--------|---------------|
| Precision | 0.994 | 99.4% des numeros flagges fraude sont vrais |
| Recall | 1.000 | 100% des vrais fraudeurs sont detectes |
| F1-Score | 0.997 | Equilibre quasi parfait |
| AUC | 1.0 | Separation parfaite fraude/normal |

- Matrice de confusion detaillee : VN=964,504 / FP=1,844 / FN=42 / VP=318,457
- Courbe ROC (figure)
- Courbe Precision-Recall (figure)
- Cross-validation 5-fold : F1 moyen = 0.9970 (+/- 0.0001)
- Feature importance : appels_par_jour (68.6%), nb_imei (23.8%), ratio_courts (3.3%)
- Distribution des scores (figure) : separation nette entre normaux et fraudes

---

## Chapitre 5 : Realisation et Deploiement (12-15 pages)

### 5.1 Environnement de developpement (2-3 pages)
- Systeme : Linux WSL (Ubuntu) sur Windows
- PostgreSQL 17 + TimescaleDB (hypertable, compression)
- Python 3.12 + virtualenv
- Librairies : Flask, XGBoost, scikit-learn, pandas, psycopg3, SQLAlchemy 2.0
- Probleme resolu : connexion WSL → Windows (detection automatique IP, pg_hba.conf)
- Probleme resolu : encodage francais (migration psycopg2 → psycopg3)
- Git + GitHub pour le versioning

### 5.2 Systeme d'authentification (3-4 pages)
- Inscription (signup) : email, username, mot de passe, role
- Verification email : code 6 chiffres envoye par Gmail SMTP
- Connexion (login) : email + mot de passe (hash avec werkzeug)
- Mot de passe oublie : code de reinitialisation par email
- Gestion de session : Flask-Login
- 2 roles : Admin (controle total) vs Analyst (lecture seule)
- Historique des connexions (table login_history)
- Captures d'ecran : pages login, signup, verification

### 5.3 Dashboard - Presentation des pages (5-6 pages)
- **Page Dashboard** : 4 cartes de stats + 2 graphiques interactifs (Chart.js)
- **Page Resultats ML** : split 70/30 visible + bouton d'evaluation en direct + explications
- **Page Prediction IA** : saisie MSISDN → prediction XGBoost en temps reel → profil du numero avec anomalies en rouge
- **Page Liste Noire** : 90,353 suspects avec features V2, recherche, pagination, boutons admin (confirmer/rejeter)
- **Page Graphiques** : 9 graphiques ML cliquables avec explications
- **Page Fraud Rules** : tableau des features + cartes des regles avec SQL
- **Page Gestion Utilisateurs** : liste des comptes, changement de role, suppression (admin only)
- Capture d'ecran de chaque page

### 5.4 Differences entre les roles (1-2 pages)
- Tableau comparatif Admin vs Analyst
- Admin : lancer evaluation, confirmer/rejeter suspects, gerer utilisateurs
- Analyst : lecture seule, prediction IA, consultation
- Captures d'ecran comparatives

### 5.5 Verification manuelle - Human-in-the-Loop (2-3 pages)
- Principe : l'IA detecte, l'humain confirme ou rejette
- Workflow : suspect detecte → admin examine → confirme fraude OU marque faux positif
- Table verification_fraude : msisdn, statut, commentaire, verifie_par, date
- Compteurs en temps reel : confirmes / faux positifs / en attente
- Importance pour eviter les fausses accusations

---

## Chapitre 6 : Tests et Discussion (8-10 pages)

### 6.1 Tests fonctionnels (3-4 pages)
- Test inscription + verification email
- Test connexion admin vs analyst (droits d'acces)
- Test prediction IA sur des numeros connus (fraudeur confirme, numero normal)
- Test evaluation ML (bouton lancer le test)
- Test verification manuelle (confirmer, rejeter)
- Test recherche dans la liste noire
- Tableau des tests : scenario, resultat attendu, resultat obtenu, statut

### 6.2 Tests de performance (2-3 pages)
- Feature Engineering : 3h11 sur 741M lignes (acceptable pour un traitement batch)
- Prediction unitaire : 0.001 sec par MSISDN (temps reel)
- Chargement dashboard : < 2 sec
- Liste noire paginee : < 1 sec par page
- Memoire utilisee : 94 Mo par le processus Python
- Problemes rencontres : disque plein (libere 100 Go), memoire epuisee (SET work_mem)

### 6.3 Discussion des resultats (3-4 pages)
- Le F1 de 0.997 est exceptionnel → discussion sur le biais circulaire (pseudo-labels = regles, modele apprend les regles)
- Limites du pseudo-labeling : le modele ne detecte pas de NOUVEAUX types de fraude
- Comparaison avec l'etat de l'art (autres travaux sur la detection SIM Box)
- Points forts du projet : donnees reelles (741M), regles entreprise, dashboard complet, human-in-the-loop
- Points faibles : pas de labels ground truth, pas de detection en temps reel (batch)
- Ameliorations possibles :
  - Labels reels (confirmes par les analystes)
  - Deep Learning (LSTM pour les sequences temporelles)
  - Detection en temps reel (streaming avec Kafka)
  - Integration des tables externes (hotlist, bypass_target_profiles, age_sim)

---

## Conclusion Generale (2-3 pages)
- Resume des realisations : systeme complet de detection de fraude SIM Box
- Chiffres cles : 741M CDR, 4.28M MSISDN, 90,353 suspects, F1=0.997
- Apports personnels : competences en Big Data, ML, developpement web, travail en entreprise
- Perspectives : deploiement en production, amelioration continue avec labels reels, extension a d'autres types de fraude

---

## Bibliographie (2 pages)
- Articles sur la detection de fraude SIM Box
- Documentation XGBoost, scikit-learn, Flask
- Documentation PostgreSQL, TimescaleDB

## Annexes (5-10 pages)
- Annexe A : Requete SQL de Feature Engineering V2 (code complet)
- Annexe B : Code Python du pipeline ML (extraits commentes)
- Annexe C : Code Flask du dashboard (extraits)
- Annexe D : Captures d'ecran supplementaires
- Annexe E : Lien GitHub du projet

---

## Estimation du nombre de pages

| Section | Pages estimees |
|---------|---------------|
| Pages preliminaires (garde, remerciements, sommaire, listes) | 6-7 |
| Introduction generale | 3-4 |
| Chapitre 1 : Cadre general | 12-15 |
| Chapitre 2 : Conception | 15-18 |
| Chapitre 3 : Feature Engineering | 12-15 |
| Chapitre 4 : Machine Learning | 15-18 |
| Chapitre 5 : Realisation | 12-15 |
| Chapitre 6 : Tests et Discussion | 8-10 |
| Conclusion | 2-3 |
| Bibliographie + Annexes | 7-12 |
| **TOTAL** | **92-117 pages** |
