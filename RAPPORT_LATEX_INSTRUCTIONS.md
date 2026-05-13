# INSTRUCTIONS POUR UTILISER LE RAPPORT LATEX

## Structure recommandee

Le fichier `rapport_pfe.tex` contient **TOUT** le contenu de ton rapport organise comme l'exemple ENET'COM. Voici comment l'utiliser :

## Option 1 : Fichier unique (le plus simple)

Tu peux mettre TOUT le contenu dans un seul fichier `rapport_pfe.tex` (sans les `\input{}`). Les commentaires `% chapitre/XX` indiquent juste les separations.

## Option 2 : Plusieurs fichiers (comme l'exemple)

Si tu veux respecter exactement la structure de l'exemple, cree un dossier `chapitre/` et copie chaque section :

```
mon_pfe_latex/
├── rapport_pfe.tex          (fichier principal, juste les \input)
├── enetcom-pfe-report.cls   (copie depuis l'exemple)
├── Commands.tex             (copie depuis l'exemple)
├── images/                  (tes screenshots)
└── chapitre/
    ├── 00-PageDeGarde.tex
    ├── 01-Dedication.tex
    ├── 02-Remerciement.tex
    ├── 03-ListeDesAbr.tex
    ├── 04-IntroductionGeneral.tex
    ├── 05-Chapitre1.tex
    ├── 06-Chapitre2.tex
    ├── 07-Chapitre3.tex
    ├── 08-ConclusionGenerale.tex
    ├── 09-Bibliographie.tex
    ├── 10-Annexes.tex
    └── 11-DosDuRapport.tex
```

## Etapes a suivre

### 1. Telecharge le template ENET'COM
Demande a ton encadrant le template original (`enetcom-pfe-report.cls` et `Commands.tex`).

### 2. Cree la structure de dossiers
```bash
mkdir mon_rapport_latex
cd mon_rapport_latex
mkdir chapitre images
```

### 3. Copie les fichiers
- Copie `enetcom-pfe-report.cls` et `Commands.tex` du template
- Copie le `rapport_pfe.tex` que je t'ai cree

### 4. Modifie la page de garde
Dans `Commands.tex`, modifie :
```latex
\newcommand{\reportTitle}{Detection de Fraude SIM Box}
\newcommand{\reportSubject}{par Machine Learning}
\newcommand{\reportAuthor}{Samar GUIZANI}
```

### 5. Ajoute tes images
Place toutes tes captures d'ecran dans le dossier `images/` :
- `usecase.png` (diagramme cas d'utilisation)
- `sequence.png` (diagramme sequence)
- `classes.png` (diagramme de classes)
- `architecture.png` (architecture technique)
- `dashboard.png` (capture du dashboard)
- `confusion_matrix.png` (matrice de confusion)
- etc.

### 6. Compile le rapport

Avec **Overleaf** (recommande) :
1. Va sur https://www.overleaf.com
2. Cree un nouveau projet
3. Upload tous les fichiers
4. Clique "Recompile"

Avec **MikTeX/TeXLive** sur Windows :
```bash
pdflatex rapport_pfe.tex
pdflatex rapport_pfe.tex
```

## Conseils anti-plagiat

Le contenu que je t'ai donne est **deja reformule** pour eviter le plagiat, mais pour etre absolument sur :

1. **Lis attentivement** chaque section
2. **Reformule** les phrases qui te semblent generiques avec tes propres mots
3. **Ajoute** tes anecdotes personnelles dans les sections "Defis rencontres"
4. **Verifie avec un detecteur** comme Turnitin avant de soumettre
5. **Cite tes sources** dans la bibliographie pour les concepts repris

## Estimation des pages

| Section | Pages estimees |
|---------|---------------|
| Page de garde | 1 |
| Dedicace | 1 |
| Remerciements | 1 |
| Table des matieres | 2 |
| Liste des figures | 1 |
| Liste des tableaux | 1 |
| Liste des abreviations | 2 |
| Introduction generale | 3 |
| Chapitre 1 | 13 |
| Chapitre 2 | 14 |
| Chapitre 3 | 15 |
| Conclusion generale | 3 |
| Bibliographie | 2 |
| Annexes | 4 |
| **TOTAL** | **~63 pages** |

Si tu veux exactement 40-45 pages pour les 3 chapitres seulement (sans les preliminaires), reduis le contenu de chaque chapitre proportionnellement.

## Que faire ensuite

1. Compile le LaTeX pour generer le PDF
2. Verifie la mise en page (chapitres, sections, figures)
3. Ajoute les captures d'ecran reels de ton dashboard dans `images/`
4. Adapte les noms (encadrant, entreprise) dans `Commands.tex`
5. Imprime ou exporte en PDF final

Bonne redaction !
