# RECAPITULATIF COMPLET DU PROJET PFE
## Document personnel - Pour ecrire le rapport sans plagiat

**Etudiant :** Samar Guizani
**Niveau :** Licence 3
**Entreprise :** Elite Business
**Annee :** 2025/2026
**Sujet :** Detection de Fraude SIM Box par Machine Learning

---

# COMMENT UTILISER CE DOCUMENT

Ce document n'est **PAS** un rapport pret a l'emploi. C'est un **journal de bord** de tout le projet. Pour ecrire ton rapport sans plagiat :

1. **Lis** chaque section attentivement
2. **Reformule** avec tes propres mots
3. **Ajoute** tes reflexions personnelles (ce que tu as appris, les difficultes rencontrees)
4. **Personnalise** avec tes propres exemples et chiffres
5. **Ne copie pas** directement les phrases : reecris-les a ta facon

---

# PARTIE 1 : LE CONTEXTE GENERAL

## Mon stage en entreprise

J'ai effectue mon stage de fin d'etudes au sein de l'entreprise **Elite Business**, qui travaille dans le secteur des telecommunications. J'ai ete affecte au departement de detection de fraude, ou j'ai pu observer les problemes reels que vivent les operateurs telecom au quotidien.

Au debut de mon stage, j'ai pris le temps de comprendre le metier. J'ai discute avec mon encadrant de l'entreprise pour comprendre quelles sont les fraudes les plus courantes dans les telecoms. Il m'a explique que la **fraude SIM Box** est un des problemes les plus graves : elle cause des pertes de revenus enormes pour les operateurs.

## La fraude SIM Box - explication simple

Avant de commencer le projet, j'ai du bien comprendre comment marche une SIM Box. Voici comment je l'ai compris :

**Une SIM Box, c'est un boitier electronique qui contient plein de cartes SIM.** Le fraudeur l'utilise pour transformer un appel international (qui coute cher) en un appel local (qui ne coute presque rien).

Concretement :
- Quelqu'un appelle de France vers la Tunisie
- Au lieu de passer par les operateurs internationaux (ce qui couterait 1 dinar par minute)
- L'appel passe par internet jusqu'a la SIM Box du fraudeur
- La SIM Box rappelle le numero tunisien comme un appel local
- L'operateur tunisien ne recoit pas l'argent de l'appel international

C'est comme si quelqu'un avait fabrique une fausse cle pour entrer dans un magasin sans payer.

## Pourquoi c'est grave pour l'operateur ?

Quand j'ai compris le mecanisme, j'ai realise pourquoi c'est un probleme important :
- **Pertes financieres directes** : chaque appel perdu, c'est de l'argent perdu
- **Saturation du reseau** : les SIM Box font des centaines d'appels, ca surcharge les antennes
- **Mauvaise qualite** : les vrais clients souffrent de la baisse de qualite
- **Probleme legal** : c'est interdit par la loi

Mon encadrant m'a montre des chiffres : selon lui, l'entreprise perd **plusieurs milliers de dinars chaque mois** a cause de ces fraudes. C'est ce qui m'a motive a faire ce projet.

---

# PARTIE 2 : LE DEFI A RELEVER

## Ce que l'entreprise faisait deja

Quand je suis arrive, l'entreprise utilisait deja des **regles SQL** pour detecter les fraudes. Par exemple :
- "Si un numero fait plus de 50 appels par jour"
- "Et si la duree moyenne est inferieure a 30 secondes"
- "Et s'il utilise plusieurs IMEI differents"
- "Alors c'est probablement une fraude"

Ces regles fonctionnaient, mais j'ai remarque plusieurs problemes :

**Probleme 1 : C'est tres lent**
Quand on lance ces regles, le systeme doit lire les **741 millions** d'enregistrements d'appels. Ca prend des heures.

**Probleme 2 : Les fraudeurs s'adaptent**
Si la regle dit "plus de 50 appels", un fraudeur intelligent fait 49 appels et echappe a la detection.

**Probleme 3 : Il n'y a pas d'interface**
Les analystes doivent ouvrir des fichiers SQL, lire des resultats bruts dans pgAdmin. Ce n'est pas pratique.

**Probleme 4 : Ca ne s'ameliore pas**
Le systeme ne devient pas plus intelligent avec le temps. C'est toujours les memes regles fixes.

## Mon objectif personnel

Apres avoir analyse la situation, je me suis fixe un objectif clair :

**"Construire un systeme moderne qui detecte les fraudes SIM Box plus rapidement et plus precisement que les regles existantes, avec une interface web pour les analystes."**

Pour atteindre cet objectif, j'ai decide d'utiliser le **Machine Learning** au lieu de seulement des regles. Le Machine Learning, c'est faire apprendre a l'ordinateur a reconnaitre les fraudes en lui montrant des exemples.

---

# PARTIE 3 : COMMENT J'AI COMMENCE

## Mes premieres semaines

### Semaine 1 : Installation de l'environnement

Le premier defi a ete d'installer tout ce dont j'avais besoin sur mon ordinateur :
- **Linux WSL** (Ubuntu) sur Windows pour avoir un environnement Linux
- **PostgreSQL** pour stocker les donnees
- **Python** avec ses librairies de Machine Learning
- **Visual Studio Code** comme editeur de code

Ca a pris plus de temps que prevu car il y a eu des conflits entre les versions.

### Semaine 1 : Premier test de connexion

Avant de commencer a coder serieusement, j'ai voulu m'assurer que mon code Python pouvait communiquer avec la base de donnees PostgreSQL. J'ai cree un petit fichier `test_connexion.py` qui se connecte simplement et affiche la version de PostgreSQL.

Quand j'ai vu **"PostgreSQL 17"** s'afficher dans mon terminal, j'etais content - la "tuyauterie" fonctionnait.

### Semaine 2 : Decouvrir les donnees

J'ai cree un fichier `explorateur.py` qui m'a permis de voir a quoi ressemblent les donnees. J'ai decouvert que chaque appel telephonique est enregistre avec 12 informations :
- Date et heure
- Type d'appel (sortant ou entrant)
- Numero de telephone
- Numero appele
- Duree
- Position GSM (lac et cell_id)
- Identifiant du telephone (IMEI)
- Et d'autres details

J'ai aussi compris que l'entreprise stocke ses donnees dans une **hypertable TimescaleDB** parce que ce sont des donnees temporelles (chaque appel a une date).

---

# PARTIE 4 : LES DEFIS TECHNIQUES

## Defi 1 : 741 millions de lignes

Tres vite, j'ai realise que je ne pouvais pas charger toutes les donnees dans la RAM de mon ordinateur. **741 millions de lignes** ca fait 83 Go ! Mon PC n'a que 16 Go de RAM.

J'ai du apprendre une regle d'or :

> **PostgreSQL est le cuisinier, Python est le serveur.**
> Le cuisinier prepare le plat dans la cuisine, et le serveur apporte juste l'assiette au client. Python ne doit jamais "porter" les 83 Go.

Concretement, j'ai modifie mes scripts pour que :
- **PostgreSQL** fait tous les calculs (GROUP BY, agregations)
- **Python** recoit juste les resultats finaux

## Defi 2 : Connexion reseau Linux ↔ Windows

Mon code tournait sur **Linux WSL**, mais la base de donnees etait sur **Windows**. Pour qu'ils puissent communiquer, j'ai du :

1. Configurer le fichier `pg_hba.conf` de PostgreSQL pour autoriser les connexions WSL
2. Configurer `postgresql.conf` pour ecouter sur toutes les adresses IP
3. Ouvrir le port 5432 dans le pare-feu Windows

J'ai aussi rencontre un probleme tordu : l'IP de Windows change a chaque redemarrage de mon PC. J'ai donc cree une fonction qui detecte l'IP automatiquement en essayant 3 methodes :
- Lire la passerelle reseau (`ip route`)
- Lire le DNS (`/etc/resolv.conf`)
- Tenter `localhost`

## Defi 3 : Encodage francais

J'ai utilise au debut le driver **psycopg2** pour Python. Mais des que le serveur PostgreSQL Windows me renvoyait une erreur en francais (avec des accents comme "e" ou "a"), psycopg2 plantait avec une erreur "UnicodeDecodeError".

Apres plusieurs heures de recherche, j'ai trouve la solution : utiliser **psycopg3** (la nouvelle version) qui gere mieux l'UTF-8.

## Defi 4 : Memoire epuisee

Quand j'ai lance ma premiere grosse requete SQL pour calculer les indicateurs, j'ai eu une erreur "memoire epuisee". PostgreSQL essayait de tout faire en RAM mais 64 Mo n'etaient pas assez.

La solution : ajouter ces parametres avant chaque requete lourde :
```sql
SET work_mem = '64MB';
SET max_parallel_workers_per_gather = 0;
```

Ca dit a PostgreSQL : "limite la memoire et n'utilise pas de processus paralleles".

---

# PARTIE 5 : LE FEATURE ENGINEERING

## C'est quoi le Feature Engineering ?

J'ai appris que pour le Machine Learning, on ne donne pas les donnees brutes a l'algorithme. On lui donne plutot des **indicateurs** (qu'on appelle "features" en anglais) calcules a partir des donnees.

Par exemple, au lieu de dire :
- "Voici 200 appels du numero +21698139995"

On dit :
- "Le numero +21698139995 a fait 200 appels au total, dont 195 sortants, avec une duree moyenne de 8 secondes, depuis 2 positions geographiques, en utilisant 1 seul IMEI"

Ces 5 chiffres resument le comportement du numero. C'est ca le Feature Engineering.

## Mes 16 indicateurs

Apres avoir etudie le comportement des SIM Box, j'ai choisi **16 indicateurs** qui me semblaient pertinents :

### Indicateurs de volume
1. **appels_sortants** : combien de fois ce numero a appele
2. **appels_entrants** : combien de fois ce numero a recu un appel

### Indicateurs de duree
3. **duree_sortants** : duree totale des appels sortants
4. **duree_entrants** : duree totale des appels entrants
5. **avg_duree_sortants** : duree moyenne d'un appel sortant
6. **avg_duree_entrants** : duree moyenne d'un appel entrant

### Indicateurs de variance
7. **variance_sortants** : pourcentage de numeros differents appeles
8. **variance_entrants** : pourcentage de numeros differents recus

La variance, c'est tres important. Si je calcule "100 appels vers seulement 5 numeros differents", la variance est de 5%. Mais si c'est "100 appels vers 100 numeros differents", la variance est 100%. Une variance proche de 100% est tres suspecte.

### Indicateurs de mobilite
9. **location_count** : nombre de positions geographiques distinctes
10. **location_count_sortants** : positions pour les sortants
11. **location_count_entrants** : positions pour les entrants

J'ai appris a combiner `lac` et `cell_id` pour avoir une position unique : `lac || '-' || cell_id`. Le code "101-12345" represente une antenne specifique.

### Indicateurs temporels
12. **active_hours** : nombre d'heures distinctes d'activite
13. **nb_jours_actifs** : nombre de jours d'activite

### Indicateurs d'equipement
14. **distinct_imei** : nombre d'appareils utilises

Un humain a 1 seul IMEI (son telephone). Une SIM Box utilise 3+ IMEI (rotation des SIM dans plusieurs boitiers).

### Indicateurs de details
15. **unique_called** : numeros distincts appeles
16. **unique_calling** : numeros distincts qui ont appele

## La grande requete SQL

J'ai ecrit une seule grosse requete SQL qui calcule ces 16 indicateurs pour chaque numero. Elle utilise `GROUP BY msisdn` pour faire le calcul et `FILTER (WHERE call_type = ...)` pour separer les appels sortants des entrants.

L'execution de cette requete a pris **6 heures et 32 minutes** sur 741 millions de lignes. C'etait long mais ca n'a ete fait qu'**une seule fois**. Apres, on a une petite table avec 4.28 millions de lignes (une par numero) qui contient toutes les features.

## Ce que ca m'a appris

J'ai compris que :
- Le Feature Engineering est l'etape **la plus importante** du Machine Learning
- C'est le metier qui guide le choix des features (l'expert me dit "regarde les IMEI, les SIM Box en utilisent plusieurs")
- Une bonne feature, c'est une feature qui **distingue** clairement les fraudes des numeros normaux

---

# PARTIE 6 : LES REGLES DE L'ENTREPRISE

## Comprendre les regles existantes

Avant de faire du Machine Learning, j'ai voulu comprendre quelles regles l'entreprise utilisait deja. Mon encadrant m'a partage ses scripts SQL.

J'ai vu des regles comme :
- **Regle Bypass IMEI** : si un numero utilise plus de 3 IMEI, c'est suspect
- **Regle Cell Location** : si un numero est dans peu de positions et a une variance elevee, c'est suspect
- **Regle Active Hours** : si un numero est actif sur peu d'heures avec une variance de 100%, c'est suspect

J'ai pris le temps de lire chaque regle et de comprendre **pourquoi** elle marche. Par exemple, la regle Active Hours fonctionne parce que les SIM Box operent souvent en "burst" sur quelques heures (genre 2h du matin) et restent silencieuses le reste du temps.

## Premiere liste noire (V1)

J'ai utilise une combinaison de ces regles pour creer ma premiere liste noire :

```
WHERE appels_sortants >= 15
  AND (variance_sortants >= 85 OR distinct_imei >= 3 OR location_count <= 3)
```

Cette requete m'a donne **70,897 suspects**. C'etait beaucoup, mais coherent avec les chiffres que mon encadrant m'avait donnes.

## Affinage avec une cell specifique

Mon encadrant m'a ensuite explique qu'une cellule particuliere, **412-54312**, est connue pour etre une zone de fraude (un quartier ou il y a des SIM Box). On peut etre encore plus precis en disant :

"Un numero est suspect SEULEMENT si tous ses appels sortants viennent de cette cell."

J'ai donc cree une **nouvelle liste noire V2** avec cette regle plus stricte. Resultat : **152 suspects** seulement, mais ce sont des **vraies fraudes**.

C'est un bon exemple du compromis en detection de fraude :
- **Regles larges** = beaucoup de suspects mais beaucoup de faux positifs
- **Regles strictes** = peu de suspects mais ce sont les vrais fraudeurs

---

# PARTIE 7 : LE MACHINE LEARNING

## Pourquoi le Machine Learning ?

J'ai compris que les regles ont des limites :
- Si je dis "variance >= 85%", un fraudeur qui a 84% passe
- Les regles ne capturent pas les **combinaisons** complexes
- Un fraudeur peut adapter son comportement

Le Machine Learning resout ces problemes en apprenant **les patterns** automatiquement, sans seuils fixes.

## Le probleme du labeling

Mais j'ai un probleme : le Machine Learning supervise a besoin de **labels** ("ce numero est fraude", "celui-la est normal"). Or, je n'ai pas de labels reels.

J'ai trouve une solution : utiliser les regles de l'entreprise pour creer des **pseudo-labels**. C'est-a-dire : "si un numero respecte les regles, je le marque comme fraude ; sinon comme normal".

C'est un peu un cercle (le ML apprend les regles), mais c'est une bonne facon de commencer. Plus tard, on remplacera les pseudo-labels par des **vraies fraudes confirmees** par les analystes.

## Le split 70/30

J'ai divise mes donnees en 2 parties :
- **70% pour entrainer** le modele (il voit les reponses)
- **30% pour tester** le modele (sans les reponses)

C'est comme un etudiant : on lui fait des cours (70%) puis on lui fait passer un examen (30%). Si il reussit l'examen, c'est qu'il a vraiment appris.

J'ai utilise `random_state=42` pour que le split soit toujours le meme - c'est important pour la reproductibilite.

## XGBoost

J'ai choisi **XGBoost** comme algorithme principal. C'est un ensemble de **200 arbres de decision** qui collaborent. Chaque arbre apprend une partie des patterns, et les decisions finales sont une combinaison de tous les arbres.

J'ai aussi utilise un parametre important : `scale_pos_weight`. Comme il y a beaucoup plus de numeros normaux que de fraudes (deséquilibre), je dois dire au modele de **donner plus de poids aux fraudes** dans son apprentissage. Sinon, il pourrait juste predire "normal" pour tout le monde et avoir 95% de precision sans rien faire d'utile.

## Isolation Forest

En parallele, j'ai aussi utilise **Isolation Forest**, un algorithme qui detecte les anomalies sans avoir besoin de labels. Le principe : il essaie d'isoler chaque point. Les points anormaux sont **faciles a isoler** (ils sont differents des autres). Les points normaux sont **difficiles a isoler** (ils sont au milieu de la foule).

C'est complementaire avec XGBoost. XGBoost apprend les regles connues, Isolation Forest peut detecter des **nouveaux types** de fraude.

## Mes resultats

### Modele V2 (avec 70,897 fraudes pseudo-labelisees)
- F1-Score = 1.0000
- Precision = 1.0000
- Recall = 1.0000
- AUC = 1.0000

C'est tres bien, mais je me suis pose des questions. Un F1 de 1.0 c'est trop parfait. J'ai compris pourquoi : le modele apprend a reproduire les memes regles qui ont genere les pseudo-labels (biais circulaire).

### Modele V3 (avec 152 vraies fraudes)
- F1-Score = 0.85
- Precision = 0.76
- Recall = 0.96
- AUC = 1.0000

C'est moins parfait, mais **plus realiste**. Ce 0.85, c'est une vraie performance. Le modele attrape 96% des vraies fraudes (Recall) et a 76% de precision.

Pour le rapport, je preciserai les **deux resultats** car ils racontent une histoire interessante : on voit l'effet du biais circulaire et l'importance d'avoir des vrais labels.

---

# PARTIE 8 : LE DASHBOARD WEB

## Pourquoi un dashboard ?

Apres avoir entraine mon modele, je me suis dit : c'est bien d'avoir un modele qui marche, mais comment les analystes vont-ils l'utiliser ? Ils ne vont pas ouvrir un terminal Python pour faire des predictions.

J'ai donc decide de creer un **dashboard web** : une interface accessible depuis un navigateur ou les analystes peuvent voir les fraudes et faire des predictions.

## Mon choix de technologies

J'ai choisi :
- **Flask** (Python) pour le backend - c'est leger et rapide a apprendre
- **HTML/CSS/JavaScript** pour le frontend - les standards du web
- **Chart.js** pour les graphiques interactifs - gratuit et simple
- **Flask-Login** pour l'authentification - bibliotheque mature

J'ai voulu eviter des frameworks plus lourds comme Django ou React qui auraient ete trop complexes pour ce projet.

## Les pages que j'ai creees

J'ai construit progressivement le dashboard, en ajoutant une page apres l'autre :

### Page Dashboard
La page d'accueil avec les statistiques globales et 2 graphiques interactifs :
- Top 10 des suspects par appels sortants
- Distribution des appels par numero

### Page Resultats ML
Cette page montre comment le modele a ete entraine et teste. Elle affiche :
- 2 cartes cote a cote : **Train (70%)** et **Test (30%)**
- Les features utilisees
- Un bouton "Lancer l'evaluation" qui execute le modele en direct
- Les resultats : F1, Precision, Recall, AUC + matrice de confusion

C'est tres pratique pour la demonstration au jury : "regardez, je clique sur ce bouton et le modele teste en direct".

### Page Prediction IA
Une page pour predire si un numero specifique est une fraude. L'analyste tape un MSISDN, le modele charge ses features depuis la base, et donne sa prediction en **0.001 seconde** (c'est instantane).

Resultat affiche :
- Verdict : **FRAUDE** (rouge) ou **NORMAL** (vert)
- Probabilite : 0% a 100%
- Profil du numero (toutes les features)

### Page Liste Noire
La liste des suspects detectes. Avec :
- Pagination (20 par page)
- Recherche par numero
- 4 boutons de filtre : par defaut, min duree, max variance, les plus suspects

J'ai aussi ajoute pour les admins des boutons "Confirmer" / "Faux positif" sur chaque ligne.

### Page Verification Manuelle
Une page reserve aux admins. C'est ici qu'ils peuvent ajouter manuellement les fraudes confirmees a 100%, ou marquer des faux positifs.

J'ai mis 2 boutons :
- **FRAUDE** (rouge) : pour les vraies fraudes confirmees
- **FAUX POSITIF** (vert) : pour les numeros accuses a tort

J'ai aussi ajoute des **suggestions** : les 50 suspects les plus dangereux apparaissent en boutons cliquables. L'admin clique sur un numero pour le pre-remplir.

### Page Graphiques
9 graphiques generés par mes scripts Python (matrice de confusion, courbe ROC, feature importance, etc.). Chaque graphique est un bouton cliquable qui ouvre l'image en grand avec une explication.

### Page Fraud Rules
Une page educative qui explique les 11 features et les regles de detection de l'entreprise.

### Page Gestion Utilisateurs
Reservée aux admins : voir tous les comptes, changer le role, supprimer un utilisateur.

## L'authentification par email

J'ai implemente un systeme d'authentification professionnel :
1. **Sign Up** : email + username + mot de passe + role
2. **Verification** : code a 6 chiffres envoye par Gmail SMTP
3. **Login** : email + mot de passe
4. **Forgot Password** : code de reinitialisation par email

J'ai utilise Gmail SMTP avec un **mot de passe d'application** (different du mot de passe normal). C'est plus securise.

## Les 2 roles

J'ai pris le temps de differencier les permissions :

**Admin** (controle total) :
- Voir le dashboard
- Lancer l'evaluation
- Faire des predictions
- Voir la liste noire
- **Confirmer/Rejeter les suspects**
- **Verification manuelle**
- **Gestion des utilisateurs**

**Analyst** (lecture seule) :
- Voir le dashboard
- Lancer l'evaluation
- Faire des predictions
- Voir la liste noire (sans boutons de validation)

Pour proteger ces actions, j'ai utilise dans Flask le decorateur `@login_required` et une verification `if current_user.is_admin`.

## Le design

Au debut, j'avais fait un design sombre (theme noir). Mais je l'ai trouve trop "technique" pour un usage professionnel. J'ai donc refait tout le design avec une palette plus moderne :
- **Sidebar dark navy** (bleu marine fonce) avec gradient
- **Couleurs claires** pour le contenu principal
- **Couleurs d'accentuation** : orange entreprise + emerald (vert success)
- **Police Inter** de Google Fonts (moderne et lisible)

J'ai aussi ajoute des petits details :
- Un point vert qui pulse a cote du logo (animation CSS)
- Des ombres douces sur les cartes
- Des transitions fluides au survol
- Un fond degrade sur la page de login

---

# PARTIE 9 : LES DEFIS ET COMMENT JE LES AI RESOLUS

## Defi : memoire epuisee dans PostgreSQL

Pendant l'execution du Feature Engineering, PostgreSQL a plante avec "out of memory". Le probleme : les calculs de COUNT(DISTINCT) sont tres gourmands en RAM.

**Solution :** ajouter `SET work_mem = '64MB'` et `SET max_parallel_workers_per_gather = 0` avant la requete. Ca limite la RAM mais permet a la requete de finir.

## Defi : timeout de pgAdmin

Quand j'executais des requetes longues (3-6h), pgAdmin se deconnectait toutes les 12 minutes avec "Connection lost".

**Solution :** lancer la requete depuis le terminal Linux avec `psql` directement, sans interface graphique. Le terminal ne se deconnecte pas.

## Defi : encodage francais avec psycopg2

Erreur "UnicodeDecodeError" quand le serveur PostgreSQL renvoyait des messages en francais.

**Solution :** migrer de **psycopg2** (ancienne version) a **psycopg3** (nouvelle version) qui gere mieux l'UTF-8.

## Defi : IP Windows qui change

A chaque redemarrage du PC, l'IP de Windows changeait, ce qui cassait ma connexion.

**Solution :** ecrire une fonction `trouver_ip_windows()` qui essaie 3 methodes pour detecter l'IP automatiquement.

## Defi : fichier `email_config.py` avec mot de passe

J'avais mis le mot de passe Gmail en clair dans le code. Si je publiais sur GitHub, n'importe qui pourrait l'utiliser.

**Solution :** ajouter `frontend/email_config.py` au fichier `.gitignore` pour qu'il ne soit pas pousse sur GitHub.

## Defi : token GitHub qui expire

Mon token d'acces GitHub allait expirer dans 7 jours.

**Solution :** regenerer le token avec **"No expiration"** pour ne plus etre embete.

---

# PARTIE 10 : MES RESULTATS

## Chiffres cles du projet

| Element | Valeur |
|---------|--------|
| Donnees brutes | 741,340,262 lignes (83 Go) |
| Numeros uniques | 4,282,822 |
| Features extraites | 16 par numero |
| Suspects (regles V1) | 70,897 |
| Vraies fraudes (regles V2) | 152 |
| Modele XGBoost V3 - F1 | 0.85 |
| Modele XGBoost V3 - Precision | 0.76 |
| Modele XGBoost V3 - Recall | 0.96 |
| Temps de prediction | 0.001 seconde |
| Pages du dashboard | 9 |
| Roles d'utilisateur | 2 (admin, analyst) |

## Comparaison avec l'existant

| Aspect | Avant (regles SQL) | Apres (mon systeme ML) |
|--------|--------------------|--------------------------|
| Vitesse | Heures | Millisecondes par numero |
| Adaptabilite | Rigide | Re-entrainable |
| Interface | pgAdmin (technique) | Dashboard web moderne |
| Validation humaine | Aucune | Page Verification Manuelle |
| Detection de combinaisons | Limitee | Capacite a apprendre des patterns |

## Ce que j'ai personnellement appris

Sur le plan **technique** :
- SQL avance (FILTER, GROUP BY, agregations sur Big Data)
- Python avec pandas, scikit-learn, XGBoost
- Flask et le developpement web
- Authentification et securite
- Git et GitHub
- HTML/CSS/JavaScript moderne

Sur le plan **transversal** :
- Travailler en environnement reel d'entreprise
- Communiquer avec un encadrant metier
- Gerer un projet sur plusieurs mois
- Documenter mon code
- Resoudre des problemes complexes par moi-meme

---

# PARTIE 11 : LIMITES ET PERSPECTIVES

## Limites de mon projet

Je dois etre honnete sur les limites :

### Limite 1 : Pseudo-labeling
Mon modele a ete entraine sur des labels generes par les regles. Donc il ne peut pas etre meilleur que les regles initiales. C'est un biais circulaire.

### Limite 2 : Pas de detection en temps reel
Le systeme fait du **batch** : on recalcule les features toutes les X heures. Pour le temps reel (detecter une fraude en cours), il faudrait du streaming (Kafka, Spark Streaming).

### Limite 3 : Tables externes manquantes
L'entreprise a des tables comme `bypass_target_profiles` (numeros cibles connus) et `hotlist_values` (zones suspectes connues) que je n'ai pas pu integrer dans mon analyse.

### Limite 4 : Volume des fraudes confirmees
Je n'ai que 152 fraudes vraiment confirmees. Pour un modele de production, il en faudrait des milliers.

## Perspectives d'amelioration

Si je devais continuer ce projet, je ferais :

1. **Re-entrainer regulierement** avec les fraudes confirmees par les analystes via la page Verification Manuelle
2. **Integrer les tables externes** de l'entreprise pour ameliorer la precision
3. **Mettre en streaming** avec Apache Kafka pour la detection en temps reel
4. **Tester d'autres algorithmes** : Random Forest, LightGBM, Deep Learning (LSTM)
5. **Application mobile** pour les analystes sur le terrain
6. **Tableau de bord pour la direction** avec ROI calcule (combien on a sauve)

---

# PARTIE 12 : CONCLUSION PERSONNELLE

Quand j'ai commence ce projet, j'avais des bases en programmation mais peu d'experience en Big Data et en Machine Learning. Aujourd'hui, je me sens beaucoup plus a l'aise.

Le projet m'a appris que :
- **Faire un projet complet est tres different de faire un exercice scolaire**. Il y a plein de petits details a gerer (versions, encodage, configuration, securite).
- **La theorie ne suffit pas**. Il faut tester, debugger, recommencer plusieurs fois.
- **L'expert metier est essentiel**. Sans mon encadrant qui m'a explique les regles, je n'aurais pas pu faire un bon projet.
- **Les chiffres trompent**. Un F1-Score de 1.0 est trop beau pour etre vrai. Il faut comprendre **pourquoi** et **dans quel contexte**.

Je suis fier du resultat : un systeme **complet** qui combine SQL avance, Machine Learning et developpement web, avec un dashboard professionnel utilise par les analystes de l'entreprise.

---

# CONSEILS POUR ECRIRE LE RAPPORT

Maintenant que tu as ce document complet, voici comment ecrire ton rapport :

## Structure recommandee

1. **Page de garde**
2. **Remerciements**
3. **Sommaire**
4. **Introduction generale** (2-3 pages)
5. **Chapitre 1 : Contexte general** (12-15 pages) - utilise la PARTIE 1, 2, 3
6. **Chapitre 2 : Conception** (15-18 pages) - utilise la PARTIE 4, 5, 6
7. **Chapitre 3 : Realisation** (15-20 pages) - utilise la PARTIE 7, 8, 9, 10
8. **Conclusion generale** (2-3 pages) - utilise la PARTIE 11, 12
9. **Bibliographie**
10. **Annexes** (code, screenshots)

## Astuces anti-plagiat

1. **Reformule chaque phrase** avec tes propres mots
2. **Ajoute des transitions** entre les paragraphes ("Apres avoir vu..., je suis passe a...")
3. **Utilise la premiere personne** : "j'ai fait", "j'ai decouvert", "j'ai eu un probleme"
4. **Donne tes propres exemples** : explique avec tes mots
5. **Ajoute tes reflexions** : "Ce que j'ai appris ici..."
6. **Cite tes sources** : si tu utilises une definition, mets une reference
7. **Verifie avec un detecteur** : utilise turnitin ou un outil similaire
8. **Demande a un ami** de lire et reformuler les phrases trop techniques

## Phrases types a utiliser

Au lieu de copier les definitions techniques, utilise des formulations comme :
- "D'apres mes observations..."
- "Le defi auquel j'ai ete confronte..."
- "J'ai constate que..."
- "Apres avoir teste plusieurs solutions..."
- "Mon analyse personnelle m'a permis de..."

---

# FIN DU DOCUMENT

Bonne redaction ! N'hesite pas a me demander si tu as besoin de plus de details sur une partie specifique.
