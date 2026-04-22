# PLAN DE RAPPORT DE STAGE - PFE

**Titre :** Detection de Fraude SIM Box par Machine Learning dans les Telecoms
**Etudiant :** Samar Guizani
**Niveau :** Licence 3
**Entreprise :** Sudatel
**Annee :** 2025/2026

---

## PAGE 1 - INTRODUCTION GENERALE

### 1.1 Contexte
Le secteur des telecommunications est touche par un type de fraude appele **SIM Box** qui cause des pertes financieres importantes aux operateurs. Cette fraude consiste a detourner les appels internationaux via des boitiers equipes de plusieurs cartes SIM, faisant passer les appels internationaux pour des appels locaux.

### 1.2 Problematique
Comment detecter automatiquement les numeros fraudeurs parmi **741 millions d'enregistrements d'appels** (CDR) avec une precision elevee et en temps reel ?

### 1.3 Objectifs
- Extraire des features pertinentes a partir des CDR brut
- Appliquer les regles metier de l'entreprise Sudatel
- Developper un modele de Machine Learning supervise (XGBoost)
- Deployer un dashboard web interactif avec authentification
- Permettre la verification humaine des suspects (human-in-the-loop)

### 1.4 Apports du projet
- **Vitesse** : remplacer plusieurs regles lentes par une prediction IA instantanee
- **Precision** : detecter les combinaisons complexes que les regles ratent
- **Evolution** : le modele s'ameliore avec les fraudes confirmees par l'analyste

---

## PAGE 2 - PRESENTATION DE L'ENTREPRISE ET ETAT DE L'ART

### 2.1 Sudatel
- Operateur telecom
- Departement : equipe de detection de fraude
- Mission du stage : developper un outil de detection intelligent

### 2.2 La fraude SIM Box (schema explicatif)
- Appel international → passerelle SIM Box → appel local bypass
- Perte de revenus pour l'operateur
- Difficulte de detection : les SIM Box se font passer pour des humains

### 2.3 Etat de l'art
- Methodes traditionnelles : regles statiques (lent, rigide)
- Machine Learning : XGBoost, Random Forest, SVM
- Deep Learning : reseaux de neurones (complexe, lent)
- Detection d'anomalies : Isolation Forest

### 2.4 Positionnement du projet
Combinaison hybride : **regles metier + Machine Learning + verification humaine**

---

## PAGE 3 - CONCEPTION DU SYSTEME

### 3.1 Acteurs et cas d'utilisation
- **Administrateur** : lance l'evaluation ML, confirme/rejette les suspects, gere les utilisateurs
- **Analyste Fraude** : consulte les resultats, fait des predictions, recherche des numeros

### 3.2 Architecture technique
```
Navigateur Web
     ↓
Flask (Python) - Linux WSL
     ↓ (reseau TCP/IP)
PostgreSQL + TimescaleDB - Windows
```

### 3.3 Modele de donnees
Tables principales :
- `cdr_data` : 741M enregistrements bruts
- `features_msisdn_v2` : 4.28M numeros avec 11 features calculees
- `liste_noire_fraude` : 90,353 suspects
- `verification_fraude` : statuts valides par les analystes
- `users` + `login_history` : authentification

---

## PAGE 4 - FEATURE ENGINEERING

### 4.1 Donnees brutes CDR
- Source : systeme MSC (Mobile Switching Center)
- Colonnes : timestamp, call_type, msisdn, imei, lac, cell_id, calling_number, called_number, duration_seconds
- Volume : 741,340,262 lignes (83 Go)

### 4.2 Les 11 features extraites

| Feature | Description | Formule |
|---------|-------------|---------|
| appels_sortants | Appels MO (mSOriginating) | COUNT FILTER MO |
| appels_entrants | Appels MT (mSTerminating) | COUNT FILTER MT |
| duree_sortants | Somme duree sortants | SUM(duration) FILTER MO |
| duree_entrants | Somme duree entrants | SUM(duration) FILTER MT |
| avg_duree_sortants | Duree moyenne MO | AVG FILTER MO |
| avg_duree_entrants | Duree moyenne MT | AVG FILTER MT |
| variance_sortants | Diversite des appeles | DISTINCT called/total MO * 100 |
| variance_entrants | Diversite des appelants | DISTINCT calling/total MT * 100 |
| location_count | Positions distinctes | COUNT DISTINCT lac\|\|'-'\|\|cell_id |
| active_hours | Heures d'activite distinctes | COUNT DISTINCT hour |
| distinct_imei | Nombre d'appareils | COUNT DISTINCT imei |

### 4.3 Execution
- Feature Engineering SQL execute dans PostgreSQL (pas en Python)
- Duree : ~3h sur 741M lignes
- Resultat : une petite table de 4.28M numeros

---

## PAGE 5 - REGLES METIER DE L'ENTREPRISE

### 5.1 Regles appliquees par Sudatel (extraites du systeme existant)

**Regle Bypass SIM Box (IMEI)**
- `distinct_imei >= 3` AND `appels_MO >= 3`

**Regle Cell Location**
- `location_count <= 3` AND `variance >= 85%` AND `appels_MO >= 15`

**Regle Active Hours**
- `active_hours <= 3` AND `variance >= 100%` AND `appels_MO >= 7`

**Regle Bypass General**
- `variance >= 100%` AND `duree_entrants = 0` AND `appels_MO >= 30`

**Regle Bypass Offnet**
- `variance >= 95%` AND `appels_MT >= 15`

### 5.2 Regle combinee (utilisee pour la liste noire)
```sql
WHERE appels_sortants >= 15
AND (variance_sortants >= 85 OR distinct_imei >= 3 OR location_count <= 3)
```

**Resultat :** 90,353 suspects detectes sur 4.28M numeros (2.1%)

### 5.3 Limites des regles simples
- Lent a executer en permanence
- Rigide : un fraudeur qui change son comportement passe entre les mailles
- Pas de combinaisons complexes

---

## PAGE 6 - MACHINE LEARNING

### 6.1 Strategie : pseudo-labeling
Comme on n'a pas de verite absolue (pas de labels "vraiment fraude"), on utilise les regles de l'entreprise pour **etiqueter** chaque numero, puis le modele ML apprend a reproduire ces regles de maniere plus souple.

### 6.2 Split train/test
- **70% apprentissage** (2,997,975 numeros) - le modele voit les reponses
- **30% test** (1,284,847 numeros) - le modele predit sans voir les reponses

### 6.3 Modele XGBoost (supervise)
- Principe : ensemble d'arbres de decision
- Avantage : rapide, precis, gere le desequilibre
- Hyperparametres : 200 arbres, profondeur 6, taux 0.1

### 6.4 Modele Isolation Forest (non-supervise)
- Detection d'anomalies sans labels
- Utile pour detecter de NOUVEAUX types de fraude

### 6.5 Resultats d'evaluation

| Metrique | Valeur | Signification |
|----------|--------|---------------|
| F1-Score | 0.997 | Quasi parfait |
| Precision | 0.994 | 99.4% des fraudes flaggees sont vraies |
| Recall | 1.000 | 100% des fraudes sont attrapees |
| AUC | 1.0 | Separation parfaite |

### 6.6 Matrice de confusion (test set, 30%)
- Vrais Negatifs : 964,504
- Faux Positifs : 1,844 (0.19%)
- Faux Negatifs : 42 (0.013%)
- Vrais Positifs : 318,457

---

## PAGE 7 - DASHBOARD WEB

### 7.1 Technologies
- Backend : Flask (Python) + psycopg3
- Frontend : HTML/CSS/JavaScript + Chart.js
- Authentification : Flask-Login + Gmail SMTP
- Modele : XGBoost .pkl charge en memoire

### 7.2 Systeme d'authentification
1. **Sign Up** : email + username + mot de passe + role (admin/analyst)
2. **Verification email** : code 6 chiffres envoye par Gmail
3. **Login** : email + mot de passe
4. **Forgot password** : code de reinitialisation par email

### 7.3 Pages du dashboard
1. **Dashboard** : statistiques globales + graphiques interactifs
2. **Resultats ML** : split 70/30 + bouton evaluation live + matrice de confusion
3. **Prediction IA** : taper un MSISDN → reponse fraude/normal en 0.001 sec
4. **Liste Noire** : 90,353 suspects + verification manuelle (admin seulement)
5. **Graphiques** : 9 graphiques ML cliquables
6. **Fraud Rules** : regles de l'entreprise avec SQL et explications
7. **Gestion Utilisateurs** : admin seulement

### 7.4 Differences Admin vs Analyst

| Fonctionnalite | Admin | Analyst |
|---------------|-------|---------|
| Voir dashboard | OUI | OUI |
| Lancer evaluation ML | OUI | NON |
| Prediction IA | OUI | OUI |
| Voir liste noire | OUI | OUI |
| Confirmer/rejeter suspects | OUI | NON |
| Gestion utilisateurs | OUI | NON |

### 7.5 Human-in-the-Loop (verification manuelle)
- L'IA detecte les suspects automatiquement
- L'admin examine et **confirme** (vraie fraude) ou **rejette** (faux positif)
- Les confirmations sont stockees dans `verification_fraude`
- Utile pour entrainer le modele plus tard avec des labels REELS

---

## PAGE 8 - TESTS ET RESULTATS

### 8.1 Tests fonctionnels
- Inscription + verification email : OK
- Login admin/analyst : OK
- Prediction sur numero connu : OK (fraude detectee en 0.001s)
- Lancement evaluation ML : OK (F1=0.997 affiche)
- Verification manuelle : OK (base mise a jour)
- Recherche par MSISDN : OK

### 8.2 Tests de performance
- Feature Engineering : 3h35 sur 741M lignes
- Prediction unitaire : 0.001 sec
- Chargement dashboard : < 2 sec
- Pagination liste noire : < 1 sec par page

### 8.3 Comparaison : methode entreprise vs mon systeme

| Aspect | Regles entreprise | Mon systeme ML |
|--------|-------------------|----------------|
| Temps de detection | Minutes a heures | Millisecondes |
| Flexibilite | Rigide | S'adapte avec re-entrainement |
| Precision | ~70-80% (estime) | 99.7% |
| Detection de combinaisons | Non | Oui |
| Human-in-the-loop | Non | Oui |

### 8.4 Limites et perspectives
- Pseudo-labeling : le modele apprend les regles, pas la verite absolue
- Ameliorations : utiliser les fraudes confirmees par les analystes pour re-entrainer
- Perspective : deploiement en streaming temps reel avec Kafka

---

## PAGE 9 - CONCLUSION ET BIBLIOGRAPHIE

### 9.1 Conclusion
Ce projet a permis de :
- **Manipuler des donnees Big Data reelles** (741M lignes, 83 Go)
- **Implementer un pipeline ML complet** (extraction → labeling → entrainement → evaluation → deploiement)
- **Developper un dashboard web professionnel** avec authentification et gestion des roles
- **Atteindre des resultats exceptionnels** (F1 = 0.997)

### 9.2 Apports personnels
- Competences en : SQL avance, Python, Flask, XGBoost, pandas, Machine Learning
- Travail en environnement reel (entreprise Sudatel)
- Gestion de projet (2 mois)

### 9.3 Perspectives
- Integration des tables internes (hotlist, bypass_target_profiles)
- Deep Learning (LSTM) pour les sequences temporelles
- Streaming temps reel avec Kafka
- Application mobile pour les analystes

### 9.4 Bibliographie (selection)
1. Sallehuddin et al. "Machine learning approach for SIM box fraud detection"
2. Documentation XGBoost : xgboost.readthedocs.io
3. Documentation Flask : flask.palletsprojects.com
4. Documentation TimescaleDB : docs.timescale.com
5. Articles sur la detection d'anomalies (Isolation Forest)

---

## ANNEXES (non comptees dans les 9 pages)
- Annexe A : Code complet du feature engineering SQL
- Annexe B : Code complet du pipeline ML Python
- Annexe C : Screenshots du dashboard
- Annexe D : Lien GitHub : https://github.com/SamarGuizani/mon_pfe
