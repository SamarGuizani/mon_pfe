# CHAPITRE 1 : CONTEXTE GENERAL ET CADRE DU PROJET

---

## Introduction du chapitre

Dans ce premier chapitre, nous presentons le cadre general dans lequel s'inscrit notre projet de fin d'etudes (PFE). Nous commencons par une presentation de l'entreprise d'accueil et de son secteur d'activite. Ensuite, nous expliquons en detail le phenomene de la **fraude SIM Box** dans les telecommunications, ses mecanismes et ses consequences economiques. Apres avoir presente l'etat de l'art des methodes de detection existantes, nous formulons la problematique de notre projet. Enfin, nous fixons les objectifs a atteindre et nous etablissons le cahier des charges qui guidera notre travail.

---

## 1.1 Presentation de l'entreprise

L'entreprise d'accueil de notre stage de fin d'etudes est un operateur dans le secteur des telecommunications. Notre stage s'est deroule au sein du **departement de detection de fraude**, une equipe specialisee dans l'identification et la prevention des comportements frauduleux qui causent des pertes financieres importantes a l'operateur.

### 1.1.1 Mission du departement

Le departement de detection de fraude a pour mission principale de :
- Surveiller en permanence le trafic des appels (CDR : Call Detail Records)
- Identifier les numeros suspects qui presentent un comportement anormal
- Bloquer les fraudeurs avant qu'ils ne causent des pertes importantes
- Maintenir la qualite de service pour les clients legitimes

### 1.1.2 Notre role pendant le stage

Pendant notre stage, nous avons participe a la **modernisation du systeme de detection** existant. L'objectif principal etait de remplacer les regles SQL rigides actuelles par un systeme intelligent base sur le **Machine Learning**, plus rapide et plus precis.

---

## 1.2 Contexte general du projet

### 1.2.1 L'industrie des telecommunications

Le secteur des telecommunications est en croissance constante avec des milliards d'appels echanges chaque jour dans le monde. Cette croissance s'accompagne malheureusement d'une augmentation des fraudes, qui representent une perte estimee a **39 milliards de dollars par an** au niveau mondial selon l'association CFCA (Communications Fraud Control Association).

### 1.2.2 Les CDR (Call Detail Records)

A chaque appel telephonique, le systeme du reseau enregistre un **CDR** qui contient toutes les informations sur cet appel :

| Champ | Description |
|-------|-------------|
| `timestamp` | Date et heure de l'appel |
| `call_type` | Type d'appel (sortant ou entrant) |
| `msisdn` | Numero de telephone |
| `imsi` | Identifiant unique de la carte SIM |
| `imei` | Identifiant unique du telephone |
| `lac` | Code de la zone geographique |
| `cell_id` | Code de l'antenne utilisee |
| `calling_number` | Numero appelant |
| `called_number` | Numero appele |
| `duration_seconds` | Duree de l'appel en secondes |

Notre operateur produit environ **741 millions de CDR** par periode d'analyse, ce qui represente un volume de **83 Go** de donnees a traiter.

---

## 1.3 La fraude SIM Box

### 1.3.1 Definition

Une **SIM Box** (aussi appelee "passerelle SIM" ou "GSM gateway") est un boitier electronique contenant plusieurs cartes SIM. Cet equipement est utilise par les fraudeurs pour **detourner les appels internationaux** et les transformer en appels locaux, evitant ainsi de payer les taxes internationales.

### 1.3.2 Mecanisme de la fraude

Le schema suivant illustre comment fonctionne une fraude SIM Box :

```
┌──────────────────────┐
│  Appelant a l'etranger │
│  (paye un appel       │
│   international)      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Operateur etranger   │
│  (route l'appel via   │
│   internet ou VoIP)   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  SIM BOX (chez le    │
│  fraudeur, en local)  │
│  - Plusieurs SIM      │
│  - Plusieurs IMEI     │
└──────────┬───────────┘
           │ (reinjecte l'appel
           │  via une carte SIM
           │  locale)
           ▼
┌──────────────────────┐
│  Destinataire local   │
│  (recoit un appel     │
│   avec un numero      │
│   local)              │
└──────────────────────┘
```

**Resultat :** L'appel international qui devait rapporter 1 dinar a l'operateur passe pour un appel local gratuit. L'operateur perd les revenus de tous les appels internationaux qui transitent par cette SIM Box.

### 1.3.3 Caracteristiques d'une SIM Box

Pour la detecter, il faut connaitre son comportement typique. Une SIM Box presente plusieurs caracteristiques particulieres qui la distinguent d'un utilisateur normal :

| Comportement | Utilisateur normal | SIM Box (fraude) |
|--------------|--------------------|--------------------|
| Nombre d'appels par jour | 5 a 20 | 100 a 1000+ |
| Appels sortants vs entrants | Equilibre | 95% sortants, 5% entrants |
| Duree des appels | 30 secondes a 5 minutes | 0 a 30 secondes |
| Numeros appeles | Famille, amis (memes numeros) | Plein de numeros differents |
| Position geographique | Bouge dans la journee | Reste fixe (boitier dans une piece) |
| Nombre d'appareils (IMEI) | 1 (son telephone) | 3 ou plus (rotation des SIM) |

### 1.3.4 Consequences financieres

Les consequences de la fraude SIM Box sont multiples et graves pour l'operateur :

1. **Pertes de revenus directes** : chaque appel international detourne represente une perte directe
2. **Saturation du reseau** : les SIM Box generent un volume anormal d'appels qui sature les ressources
3. **Degradation de la qualite** : les clients legitimes subissent une mauvaise qualite de service
4. **Probleme legal** : la fraude SIM Box est illegale dans la plupart des pays
5. **Image de l'entreprise** : l'incapacite a detecter ces fraudes nuit a la reputation

---

## 1.4 Etat de l'art : les methodes de detection existantes

Plusieurs approches ont ete proposees dans la litterature pour detecter les fraudes SIM Box. Nous les classons en trois grandes categories.

### 1.4.1 Approche 1 : Les regles statiques

C'est la methode **traditionnelle** utilisee actuellement par notre entreprise. Elle consiste a definir des **seuils** sur certains indicateurs et a alerter quand ces seuils sont depasses.

**Exemple de regle :**
```
SI nombre d'appels > 50
ET duree moyenne < 30 secondes
ET nombre d'IMEI >= 3
ALORS fraude detectee
```

**Avantages :**
- Simple a comprendre et a implementer
- Rapide a mettre en place
- Decisions explicables

**Inconvenients :**
- **Rigide** : un fraudeur intelligent peut ajuster son comportement pour passer juste sous les seuils
- **Lent** : les regles doivent scanner toute la base de donnees a chaque execution
- **Manuel** : les seuils doivent etre ajustes manuellement par les analystes
- **Aveugle aux combinaisons** : ne detecte pas les patterns complexes

### 1.4.2 Approche 2 : Le Machine Learning supervise

Cette approche utilise des algorithmes qui **apprennent** a partir d'exemples de fraudes connues. Les modeles les plus utilises sont :

- **Random Forest** : ensemble d'arbres de decision
- **SVM** (Support Vector Machine) : separation par hyperplan
- **XGBoost** : Gradient Boosting tres performant
- **Reseaux de neurones** : modeles plus complexes

**Avantages :**
- Detecte les **combinaisons** complexes que les regles ratent
- **Rapide** en prediction (millisecondes par numero)
- S'adapte aux **nouveaux** types de fraude

**Inconvenients :**
- Necessite des **donnees etiquetees** (fraude vs normal)
- Peut etre une **boite noire** difficile a expliquer
- Risque de **sur-apprentissage**

### 1.4.3 Approche 3 : Le Machine Learning non supervise

Cette approche detecte les **anomalies** sans avoir besoin de labels prealables. L'algorithme apprend ce qui est "normal" et signale tout comportement different.

**Algorithmes principaux :**
- **Isolation Forest** : isole les points anormaux
- **DBSCAN** : detection de clusters
- **Autoencoders** : reseaux de neurones pour reconstruction

**Avantages :**
- Pas besoin de labels
- Detecte des fraudes **inconnues**
- Adaptable

**Inconvenients :**
- Plus de **faux positifs**
- Difficile d'interpreter les resultats

### 1.4.4 Tableau comparatif

| Critere | Regles | ML supervise | ML non supervise |
|---------|--------|--------------|--------------------|
| Vitesse de detection | Lente | Rapide | Rapide |
| Necessite de labels | Non | Oui | Non |
| Detecte les patterns complexes | Non | Oui | Partiellement |
| Detecte les nouvelles fraudes | Non | Limite | Oui |
| Facilite d'explication | Tres facile | Moyenne | Difficile |

---

## 1.5 Problematique du projet

### 1.5.1 Constats actuels

Apres avoir analyse le systeme existant de notre entreprise, nous avons identifie plusieurs problemes :

1. **Lenteur** : les regles SQL doivent scanner les 741 millions de CDR a chaque execution, ce qui prend plusieurs heures
2. **Rigidite** : les fraudeurs adaptent leur comportement pour eviter les seuils fixes
3. **Pas d'apprentissage** : le systeme ne s'ameliore pas avec le temps
4. **Pas d'interface** : les analystes utilisent des fichiers SQL bruts difficiles a interpreter
5. **Pas de validation humaine** : aucun mecanisme pour valider les fraudes detectees

### 1.5.2 Problematique

A partir de ces constats, nous formulons la problematique de notre projet :

> **Comment detecter automatiquement les fraudeurs SIM Box parmi 741 millions d'enregistrements CDR avec une precision elevee, en quasi temps reel, et avec une interface utilisable par les analystes, tout en permettant l'amelioration continue du systeme grace a la validation humaine ?**

Cette problematique se decompose en plusieurs sous-questions :

- Comment traiter efficacement un volume aussi important de donnees (Big Data) ?
- Comment combiner la connaissance metier (regles) avec l'intelligence artificielle (ML) ?
- Comment evaluer si notre modele fonctionne reellement bien ?
- Comment integrer une validation humaine pour ameliorer le systeme ?
- Comment presenter les resultats de maniere claire aux analystes ?

---

## 1.6 Objectifs du projet

Pour repondre a la problematique, nous fixons les objectifs suivants :

### 1.6.1 Objectif general

Developper un **systeme intelligent et complet** de detection de fraude SIM Box, qui combine les regles metier de l'entreprise avec des algorithmes de Machine Learning, et qui soit accessible via une **interface web professionnelle**.

### 1.6.2 Objectifs specifiques

| Numero | Objectif |
|--------|----------|
| **O1** | Mettre en place une connexion stable entre Python (Linux) et PostgreSQL (Windows) |
| **O2** | Extraire les indicateurs (features) pertinents a partir des CDR bruts |
| **O3** | Implementer un pipeline Machine Learning complet (entrainement + evaluation) |
| **O4** | Atteindre une precision elevee (F1-Score superieur a 0.80) |
| **O5** | Developper un dashboard web avec authentification et gestion des roles |
| **O6** | Permettre la validation humaine des suspects (Human-in-the-Loop) |
| **O7** | Documenter le projet pour qu'il soit reutilisable |

---

## 1.7 Cahier des charges

Pour atteindre ces objectifs, nous etablissons un cahier des charges precis, divise en besoins fonctionnels et besoins non-fonctionnels.

### 1.7.1 Besoins fonctionnels

Les besoins fonctionnels decrivent ce que le systeme **doit faire** :

#### A. Gestion des donnees
- **BF1** : Lire les CDR depuis la base de donnees PostgreSQL
- **BF2** : Calculer 16 indicateurs (features) pour chaque numero de telephone
- **BF3** : Sauvegarder les resultats dans une nouvelle table optimisee

#### B. Detection de fraude
- **BF4** : Appliquer les regles metier de l'entreprise pour creer une liste noire
- **BF5** : Entrainer un modele Machine Learning (XGBoost) sur les donnees etiquetees
- **BF6** : Predire si un numero donne est une fraude ou non
- **BF7** : Calculer les metriques d'evaluation du modele (F1, Precision, Recall, AUC)

#### C. Dashboard web
- **BF8** : Permettre la connexion avec authentification par email
- **BF9** : Afficher les statistiques globales (Dashboard)
- **BF10** : Afficher les resultats du Machine Learning (Resultats ML)
- **BF11** : Permettre la prediction sur un numero specifique (Prediction IA)
- **BF12** : Afficher la liste noire des suspects avec filtres avances
- **BF13** : Afficher les graphiques d'evaluation du modele
- **BF14** : Afficher les regles de detection de l'entreprise
- **BF15** : Permettre la validation manuelle des fraudes (admin)
- **BF16** : Permettre l'ajout de faux positifs (admin)
- **BF17** : Gerer les utilisateurs (admin)

#### D. Roles et permissions
- **BF18** : Distinguer 2 roles : **Administrateur** et **Analyste**
- **BF19** : Restreindre certaines fonctions aux admins seulement

### 1.7.2 Besoins non-fonctionnels

Les besoins non-fonctionnels decrivent **comment** le systeme doit fonctionner :

| Besoin | Description |
|--------|-------------|
| **BNF1 - Performance** | La prediction doit etre instantanee (< 100 millisecondes) |
| **BNF2 - Volume** | Le systeme doit traiter 741 millions de CDR sans saturer la memoire |
| **BNF3 - Securite** | Authentification obligatoire, mots de passe hashes, sessions securisees |
| **BNF4 - Disponibilite** | Le dashboard doit etre accessible 24/7 |
| **BNF5 - Utilisabilite** | Interface intuitive, comprehensible par un analyste non technique |
| **BNF6 - Compatibilite** | Compatible avec les navigateurs modernes (Chrome, Firefox, Edge) |
| **BNF7 - Maintenabilite** | Code documente, modulaire, versionne sur GitHub |
| **BNF8 - Adaptabilite** | Le modele doit pouvoir etre re-entraine avec de nouvelles donnees |

### 1.7.3 Contraintes techniques

| Contrainte | Justification |
|------------|---------------|
| **Base de donnees** : PostgreSQL avec TimescaleDB | Imposee par l'entreprise (donnees existantes) |
| **Systeme d'exploitation** : Linux WSL pour le developpement | Standard du metier en Data Science |
| **Langage** : Python 3.12 | Ecosysteme ML mature (scikit-learn, XGBoost, pandas) |
| **Framework web** : Flask | Leger, rapide a mettre en place |
| **Driver DB** : psycopg3 | Resout les problemes d'encodage avec le serveur Windows |
| **Versioning** : Git + GitHub | Standard professionnel |

---

## 1.8 Methodologie adoptee

Pour mener a bien ce projet, nous avons adopte une methodologie en **5 phases** progressives :

### Phase 1 : Analyse et conception
- Comprendre le metier et les besoins
- Explorer les donnees existantes
- Identifier les indicateurs pertinents
- Definir l'architecture technique

### Phase 2 : Feature Engineering
- Ecrire les requetes SQL pour extraire les indicateurs
- Optimiser pour le Big Data (741 millions de lignes)
- Creer une table de features reutilisable

### Phase 3 : Pipeline Machine Learning
- Etiqueter les donnees avec les regles de l'entreprise
- Diviser les donnees en 70% entrainement / 30% test
- Entrainer XGBoost et Isolation Forest
- Evaluer avec les metriques standard (F1, Precision, Recall, AUC)

### Phase 4 : Developpement du dashboard
- Backend Flask avec authentification
- Frontend HTML/CSS/JavaScript moderne
- Integration du modele ML pour predictions en temps reel

### Phase 5 : Validation et documentation
- Tests fonctionnels et de performance
- Documentation complete
- Versionnement sur GitHub

---

## 1.9 Architecture du systeme propose

L'architecture globale de notre systeme se decompose en 3 couches principales :

```
┌─────────────────────────────────────────────────────────┐
│  COUCHE PRESENTATION (Frontend)                          │
│  - HTML / CSS / JavaScript                               │
│  - Chart.js pour les graphiques                          │
│  - Design moderne (Navy + Emerald)                       │
└─────────────────────────────────────────────────────────┘
                          ▲
                          │ HTTP / JSON
                          ▼
┌─────────────────────────────────────────────────────────┐
│  COUCHE APPLICATION (Backend)                            │
│  - Flask (Python)                                        │
│  - Flask-Login (authentification)                        │
│  - SQLAlchemy (ORM)                                      │
│  - XGBoost (modele ML charge en memoire)                 │
└─────────────────────────────────────────────────────────┘
                          ▲
                          │ TCP/IP (port 5432)
                          ▼
┌─────────────────────────────────────────────────────────┐
│  COUCHE DONNEES (Database)                               │
│  - PostgreSQL 17                                         │
│  - TimescaleDB (hypertables pour les series temporelles) │
│  - 741 millions de CDR                                   │
│  - Tables : users, features, liste_noire, verification   │
└─────────────────────────────────────────────────────────┘
```

### 1.9.1 Architecture reseau particuliere

Notre projet a une **specificite technique** : la base de donnees se trouve sur **Windows** alors que notre code Python tourne sur **Linux WSL**. Pour communiquer, ils utilisent le reseau local TCP/IP.

```
[Linux WSL]  ←─── Reseau local ───→  [Windows]
 Python                                PostgreSQL
 Flask                                 (741 millions CDR)
 XGBoost
```

Cette architecture nous a oblige a :
- Configurer `pg_hba.conf` pour autoriser les connexions WSL
- Detecter automatiquement l'IP de Windows (qui change a chaque redemarrage)
- Utiliser psycopg3 au lieu de psycopg2 (probleme d'encodage)

---

## 1.10 Innovations apportees

Notre projet apporte plusieurs innovations par rapport au systeme existant :

### Innovation 1 : Approche hybride
Nous combinons **3 approches complementaires** :
1. Les **regles metier** de l'entreprise pour creer les pseudo-labels
2. Le **Machine Learning supervise** (XGBoost) pour la generalisation
3. La **detection d'anomalies** (Isolation Forest) pour les nouveaux types de fraude

### Innovation 2 : Validation humaine
Nous ajoutons une etape de **validation manuelle** par l'administrateur :
- Confirmation des vraies fraudes
- Marquage des faux positifs
- Re-entrainement futur avec ces vraies donnees

### Innovation 3 : Dashboard professionnel
Nous remplacons les fichiers SQL bruts par une **interface web moderne** :
- Sidebar de navigation claire
- Graphiques interactifs
- Authentification par email avec verification
- 2 roles distincts (admin / analyste)

### Innovation 4 : Pipeline reutilisable
Tout le pipeline est **modulaire et reutilisable** :
- Chaque etape est un script independant
- Le code est documente et versionne sur GitHub
- L'entreprise peut continuer le projet apres notre depart

---

## 1.11 Resultats attendus

A la fin de ce projet, nous esperons obtenir :

1. **Une base de donnees enrichie** avec 16 indicateurs par numero de telephone
2. **Une liste noire precise** contenant les vraies fraudes confirmees
3. **Un modele Machine Learning** avec un F1-Score superieur a 0.80
4. **Un dashboard web fonctionnel** avec toutes les pages prevues
5. **Une documentation complete** du projet (rapport, code, GitHub)
6. **Un systeme reutilisable** que l'entreprise peut continuer a utiliser

---

## 1.12 Planning previsionnel

Le projet a ete realise en plusieurs etapes, etalees sur la duree du stage :

| Periode | Activite |
|---------|----------|
| **Semaine 1-2** | Decouverte de l'entreprise, exploration des donnees |
| **Semaine 3-4** | Feature Engineering SQL, optimisation Big Data |
| **Semaine 5-6** | Pipeline Machine Learning (entrainement, evaluation) |
| **Semaine 7-8** | Developpement du backend Flask et de l'authentification |
| **Semaine 9-10** | Developpement du frontend (pages, design, graphiques) |
| **Semaine 11** | Tests, validation, integration de la verification humaine |
| **Semaine 12** | Documentation, redaction du rapport |

---

## Conclusion du chapitre

Dans ce premier chapitre, nous avons pose les bases de notre projet de fin d'etudes. Nous avons presente l'entreprise d'accueil, le contexte de la fraude SIM Box, et nous avons analyse les methodes de detection existantes avec leurs avantages et leurs limites.

Nous avons formule la **problematique** centrale du projet : detecter automatiquement les fraudeurs SIM Box dans un volume de 741 millions de CDR avec precision et rapidite, tout en proposant une interface utilisable et la possibilite de validation humaine.

Pour repondre a cette problematique, nous avons fixe **7 objectifs** specifiques et redige un **cahier des charges** detaille comprenant 19 besoins fonctionnels et 8 besoins non-fonctionnels. Nous avons egalement decrit la **methodologie en 5 phases** que nous avons adoptee, ainsi que **l'architecture technique** du systeme propose.

Notre projet apporte plusieurs **innovations** : une approche hybride (regles + ML + anomalies), une validation humaine integree (Human-in-the-Loop), un dashboard professionnel moderne, et un pipeline modulaire et reutilisable.

Dans le **chapitre 2**, nous detaillerons la **conception du systeme** : les diagrammes UML (cas d'utilisation, sequence, classes), le modele de donnees, et les choix techniques justifies. Le **chapitre 3** sera consacre a la **realisation pratique** du projet, avec les scripts SQL, le pipeline ML, le dashboard, et les resultats obtenus.

---
