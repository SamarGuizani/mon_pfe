# Resume Complet du Projet PFE
## Detection de Fraude SIM Box dans les Telecoms

**Etudiant :** Samar Guizani
**Niveau :** Licence 3 (PFE)
**Entreprise :** Sudatel
**Duree :** 2026
**GitHub :** https://github.com/SamarGuizani/mon_pfe

---

## 1. RESUME DU PROJET EN 1 PARAGRAPHE

Ce projet consiste a developper un systeme intelligent de detection de fraude SIM Box pour un operateur telecom. A partir de **741 millions de lignes CDR** (Call Detail Records, 83 Go), nous avons extrait des features comportementales (variance des appels, mobilite, IMEI, heures d'activite) basees sur les **regles reelles de l'entreprise**. Un modele de Machine Learning **XGBoost** a ete entraine sur 70% des donnees et teste sur 30%, atteignant un **F1-Score de 0.997** (99.7% de precision). Un dashboard web Flask avec authentification par email permet aux analystes de visualiser les resultats et aux administrateurs de confirmer ou rejeter les suspects.

---

## 2. CE QU'ON A FAIT (resume technique)

### Backend (connexion + donnees)
- Connexion **Python (Linux WSL) → PostgreSQL/TimescaleDB (Windows)** via le reseau
- Detection automatique de l'IP Windows (change a chaque redemarrage)
- Migration psycopg2 → psycopg3 (probleme d'encodage francais)
- Feature Engineering SQL sur **741M lignes** (scan de 3h) :
  - 11 features extraites : appels sortants/entrants, duree, variance, locations (lac+cell), heures actives, IMEI
  - Regles basees sur celles de **Sudatel** (variance >= 85%, IMEI >= 3, locations <= 3)

### Machine Learning
- **Split 70/30** : 70% apprentissage, 30% test
- **Pseudo-labeling** : regles metier de l'entreprise pour etiqueter fraude/normal
- **2 modeles** :
  - **XGBoost** (supervise) : F1 = 0.997, AUC = 1.0, 42 faux negatifs sur 318K fraudes
  - **Isolation Forest** (non-supervise) : detection d'anomalies sans labels
- **3 methodes de detection d'outliers** : Z-Score, IQR, Isolation Forest avec vote consensus
- **9 graphiques** : matrice de confusion, courbe ROC, feature importance, etc.

### Frontend (dashboard Flask)
- **7 pages** : Dashboard, Resultats ML, Prediction IA, Liste Noire, Graphiques, Fraud Rules, Gestion Utilisateurs
- **Authentification par email** : signup → code de verification → login
- **2 roles** : Admin (controle total) vs Analyst (lecture seule)
- **Prediction en temps reel** : taper un MSISDN → l'IA repond fraude/normal en 0.001 sec
- **Verification manuelle** : l'admin confirme ou rejette les suspects (human-in-the-loop)
- **Design** : sidebar gauche, couleurs jaune/blanc

### Resultats
- **4,282,822 MSISDN** analyses
- **90,353 suspects** detectes avec les regles de l'entreprise
- **F1 = 0.997** sur les donnees de test (30%)
- **Dashboard fonctionnel** avec login, prediction IA, et gestion des roles

---

## 3. TECHNOLOGIES UTILISEES

| Categorie | Technologie |
|-----------|------------|
| Langage backend | Python 3.12 |
| Framework web | Flask |
| Base de donnees | PostgreSQL 17 + TimescaleDB |
| Machine Learning | XGBoost, Isolation Forest (scikit-learn) |
| Data | Pandas, NumPy |
| Graphiques | Matplotlib, Seaborn, Chart.js |
| Frontend | HTML, CSS, JavaScript |
| Authentification | Flask-Login, Gmail SMTP |
| Versioning | Git, GitHub |
| Environnement | Linux WSL (Ubuntu) sur Windows |

---

## 4. ARCHITECTURE DU SYSTEME

```
┌──────────────────────────────────────────────────────────┐
│                    NAVIGATEUR WEB                         │
│  Dashboard / Prediction IA / Liste Noire / Graphiques    │
└──────────────────┬───────────────────────────────────────┘
                   │ HTTP (port 5000)
┌──────────────────▼───────────────────────────────────────┐
│              FLASK (Python - Linux WSL)                    │
│  - Routes + API REST                                      │
│  - XGBoost .pkl (charge au demarrage)                     │
│  - Authentification (Flask-Login)                         │
│  - Envoi emails (Gmail SMTP)                              │
└──────────────────┬───────────────────────────────────────┘
                   │ TCP/IP (port 5432)
┌──────────────────▼───────────────────────────────────────┐
│         POSTGRESQL + TIMESCALEDB (Windows)                 │
│  - cdr_data : 741M lignes CDR (83 Go)                     │
│  - features_msisdn_v2 : 4.28M MSISDN (11 features)       │
│  - liste_noire_fraude : 90,353 suspects                   │
│  - users : comptes admin/analyst                          │
│  - verification_fraude : statuts confirme/faux_positif    │
│  - login_history : historique des connexions              │
└──────────────────────────────────────────────────────────┘
```

---

## 5. PIPELINE MACHINE LEARNING

```
ETAPE 1 : Feature Engineering (PostgreSQL, 3h)
  741M lignes CDR → GROUP BY msisdn → 4.28M lignes avec 11 features

ETAPE 2 : Labeling (Python, 1 min)
  Regles entreprise → pseudo-labels (fraude/normal)

ETAPE 3 : Split (Python, 1 min)
  4.28M → 70% train (3M) + 30% test (1.28M)

ETAPE 4 : Entrainement (Python, 5 min)
  XGBoost apprend sur les 70% (avec les reponses)

ETAPE 5 : Evaluation (Python, 2 min)
  XGBoost predit sur les 30% (sans les reponses)
  Resultat : F1 = 0.997, AUC = 1.0

ETAPE 6 : Deploiement
  Modele .pkl → Flask → API prediction en temps reel
```

---

# PLAN DE RAPPORT DE STAGE

## Page de garde
- Titre : "Detection de Fraude SIM Box par Machine Learning dans les Telecoms"
- Etudiant : Samar Guizani
- Universite : [ton universite]
- Entreprise : Sudatel
- Encadrant : [nom du prof]
- Annee : 2025/2026

## Remerciements (1 page)

## Sommaire

## Introduction generale (2-3 pages)
- Contexte : la fraude SIM Box dans les telecoms
- Problematique : comment detecter automatiquement les SIM Box parmi des millions d'appels ?
- Objectif : developper un systeme intelligent de detection base sur le Machine Learning
- Plan du rapport

---

## Chapitre 1 : Presentation de l'entreprise et du contexte (8-10 pages)

### 1.1 Presentation de l'entreprise
- Sudatel : operateur telecom
- Secteur d'activite, taille, services

### 1.2 Qu'est-ce qu'une SIM Box ?
- Definition : boitier physique avec plusieurs SIM
- Comment ca marche : appel international → SIM Box → appel local (bypass)
- Impact financier : perte de revenus pour l'operateur
- Schema explicatif de la fraude

### 1.3 Etat de l'art
- Methodes existantes de detection (regles, ML, deep learning)
- Travaux anterieurs (2-3 articles)
- Limites des approches actuelles

### 1.4 Problematique et objectifs
- Detection automatique sur des donnees massives (741M lignes)
- Combinaison regles metier + Machine Learning
- Dashboard web pour les analystes

---

## Chapitre 2 : Conception (10-12 pages)

### 2.1 Architecture globale du systeme
- Schema : PostgreSQL → Python → Flask → Navigateur
- Explication de chaque composant

### 2.2 Diagramme de cas d'utilisation (Use Case)
- Acteurs : Admin, Analyst
- Cas : se connecter, voir dashboard, predire fraude, verifier suspects, gerer utilisateurs

### 2.3 Diagramme de classes
- Classes : User, MSISDN, Feature, Prediction, Verification

### 2.4 Diagramme de sequence
- Sequence : login → dashboard → prediction IA → verification

### 2.5 Modele de donnees (MCD/MLD)
- Tables : cdr_data, features_msisdn_v2, liste_noire_fraude, users, verification_fraude, login_history
- Relations entre les tables

### 2.6 Choix techniques
- Pourquoi PostgreSQL + TimescaleDB (hypertable, compression)
- Pourquoi Python + Flask (simplicite, scikit-learn)
- Pourquoi XGBoost (performance, donnees desequilibrees)

---

## Chapitre 3 : Feature Engineering et Regles de Detection (8-10 pages)

### 3.1 Donnees brutes (CDR)
- 741,340,262 lignes, 12 colonnes
- Types d'appels : mSOriginating (MO), mSTerminating (MT), callForwarding
- Periode couverte

### 3.2 Features extraites
- Tableau des 11 features avec formule SQL et justification
- Appels : sortants, entrants, total
- Duree : totale, moyenne
- Variance : diversite des appeles/appelants
- Mobilite : locations (lac+cell_id)
- Temporel : heures actives, jours actifs
- Equipement : IMEI distincts

### 3.3 Regles de detection de l'entreprise
- 6 regles detaillees (Bypass General, SIM Box IMEI, Cell Location, Active Hours, Bypass Offnet, Regle combinee)
- Seuils : variance >= 85%, IMEI >= 3, locations <= 3, appels MO >= 15
- Justification de chaque seuil

### 3.4 Resultat du Feature Engineering
- 4,282,822 MSISDN uniques
- 90,353 suspects detectes par les regles
- Statistiques descriptives des features

---

## Chapitre 4 : Machine Learning (10-12 pages)

### 4.1 Probleme du labeling
- Pas de labels ground truth disponibles
- Solution : pseudo-labeling a partir des regles metier
- Limites de cette approche (a mentionner)

### 4.2 Split des donnees
- 70% train (2,997,975 MSISDN) / 30% test (1,284,847 MSISDN)
- Pourquoi 70/30 (standard en ML)
- random_state=42 pour reproductibilite

### 4.3 Modele XGBoost (supervise)
- Qu'est-ce que XGBoost ? (ensemble d'arbres de decision, gradient boosting)
- Hyperparametres : n_estimators=200, max_depth=6, learning_rate=0.1
- scale_pos_weight pour les donnees desequilibrees
- Entrainement : 5 min sur 3M lignes

### 4.4 Modele Isolation Forest (non-supervise)
- Principe : isoler les anomalies (points faciles a separer)
- contamination=0.05 (5% estimes fraudeurs)
- Comparaison avec XGBoost

### 4.5 Evaluation du modele
- **Pourquoi pas l'accuracy** (donnees desequilibrees)
- Metriques utilisees :
  - F1-Score = 0.997
  - Precision = 0.994
  - Recall = 1.000
  - AUC = 1.0
- Matrice de confusion : 964,504 VN / 1,844 FP / 42 FN / 318,457 VP
- Courbe ROC
- Cross-validation 5-fold : F1 moyen = 0.9970

### 4.6 Feature Importance
- Top 3 : appels_par_jour (68.6%), nb_imei (23.8%), ratio_appels_courts (3.3%)
- Interpretation : l'intensite d'appels et le nombre d'appareils sont les meilleurs indicateurs

### 4.7 Detection d'outliers (3 methodes)
- Z-Score : 125,291 outliers (2.93%)
- IQR : 636,831 outliers (14.87%)
- Isolation Forest : 214,142 outliers (5.00%)
- Vote consensus (>=2 methodes) : 216,249 suspects (5.05%)

---

## Chapitre 5 : Realisation et Dashboard (8-10 pages)

### 5.1 Architecture technique
- Linux WSL (Python) ↔ Windows (PostgreSQL) via reseau TCP
- Detection automatique de l'IP Windows
- Flask + XGBoost .pkl

### 5.2 Authentification
- Inscription par email avec code de verification (6 chiffres)
- Connexion par email + mot de passe
- Mot de passe oublie → code par email
- 2 roles : Admin (controle total) vs Analyst (lecture seule)

### 5.3 Pages du dashboard (screenshots)
1. **Dashboard** : stats globales + graphiques interactifs
2. **Resultats ML** : split 70/30 visible + bouton d'evaluation en direct
3. **Prediction IA** : taper un MSISDN → prediction en temps reel
4. **Liste Noire** : 90,353 suspects avec features V2
5. **Graphiques** : 9 graphiques ML cliquables
6. **Fraud Rules** : regles de l'entreprise avec SQL
7. **Gestion Utilisateurs** : admin peut supprimer/changer les roles

### 5.4 Differences Admin vs Analyst
- Tableau comparatif des fonctionnalites par role
- Admin : lancer evaluation, confirmer/rejeter, gerer users
- Analyst : lecture seule, prediction IA

### 5.5 Verification manuelle (Human-in-the-Loop)
- L'IA detecte → l'admin confirme ou rejette
- Table verification_fraude en base
- Compteurs : confirmes / faux positifs / en attente

---

## Chapitre 6 : Tests et Resultats (4-6 pages)

### 6.1 Tests fonctionnels
- Login admin/analyst
- Prediction sur des numeros connus (fraudeurs et normaux)
- Verification manuelle

### 6.2 Tests de performance
- Feature Engineering : 3h11 sur 741M lignes
- Prediction : 0.001 sec par MSISDN
- Dashboard : temps de chargement < 2 sec

### 6.3 Resultats comparatifs
| Modele | Precision | Recall | F1 | AUC |
|--------|-----------|--------|-----|-----|
| Regles seules (baseline) | - | - | - | - |
| Isolation Forest | - | - | - | - |
| **XGBoost** | **0.994** | **1.000** | **0.997** | **1.0** |

### 6.4 Discussion
- Le F1 de 0.997 est tres eleve → possible overfitting sur les pseudo-labels
- Limites : pas de labels ground truth, dependance aux regles metier
- Ameliorations possibles : deep learning, donnees labelisees reelles

---

## Conclusion generale (2 pages)
- Resume des realisations
- Apports du stage (techniques et personnels)
- Perspectives : deploiement en production, modeles plus complexes, donnees en temps reel

## Bibliographie

## Annexes
- Annexe A : Code source principal (extraits)
- Annexe B : Requetes SQL de Feature Engineering
- Annexe C : Screenshots du dashboard
- Annexe D : GitHub du projet
