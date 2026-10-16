# Crédits

## BodyParts3D

Les modèles 3D de ce dépôt sont des adaptations de **BodyParts3D**,
© The Database Center for Life Science (DBCLS), licence
[CC BY-SA 2.1 Japon](https://creativecommons.org/licenses/by-sa/2.1/jp/).

> BodyParts3D, © The Database Center for Life Science licensed under CC Attribution-Share Alike 2.1 Japan

Source : <https://dbarchive.biosciencedbc.jp/en/bodyparts3d/>

| Version | Fichiers | Utilisés pour |
|---|---|---|
| 4.0 (2013) | `isa_BP3D_4.0_obj_99`, `partof_BP3D_4.0_obj_99`, listes de parties et arbres is-a / part-of | Corps entier ; vaisseaux du membre supérieur ; noms et arbres FMA |
| 3.0 (2011-09-15) | `BodyParts3D_3.0_obj_95`, `20110915/parts_list_e.txt`, `20110915/composite_parts.txt` | Os et muscles du membre supérieur (maillages plus denses) ; 77 structures de `full_body` absentes de la 4.0 (muscles surtout) ; noms et composition des concepts 3.0 |

Les identifiants et les noms anglais des structures (`FMA…`) viennent de la
**Foundational Model of Anatomy** (Structural Informatics Group, University of Washington,
licence CC BY 3.0), telle que reprise par BodyParts3D.

## Open3DModel (nerfs du membre supérieur)

Les **nerfs** du modèle `upper_limb` viennent de l'**Open3DModel**, projet « Open 3D Anatomical
Model for Education » (Leiden University Medical Center, Radboud UMC et autres, publié sur
AnatomyTOOL), licence [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
Crédit demandé par AnatomyTOOL (<https://anatomytool.org/node/63906>) :

> "Open3DModel - Upper limb - English labels" at AnatomyTOOL.org by Open3D project, Jan Kooloos,
> RadboudUMC, Eungyeol Lee, LUMC et al, license: Creative Commons Attribution-ShareAlike

Contenu anatomique : Jan (J.) Kooloos, PhD, anatomist em., Radboud University Nijmegen, dept. Anatomy ;
prof. Marco (M.C.) DeRuiter, PhD, Leiden University Medical Center (LUMC), dept. Anatomy & Embryology ;
Denise (D.M.J.) Arnold, MD, University of Toronto (vaisseaux et nerfs) ; Prof. em. George J.R. Maat,
MD, PhD, LUMC (os et articulations). Modélisation 3D : Eungyeol Lee, BFA, MSI, LUMC. Modèle web :
Daniël Jansma, MSc, LUMC. L'Open3DModel s'appuie sur BodyParts3D et Z-Anatomy (CC BY-SA 4.0) ; ses
nerfs du membre supérieur ont été entièrement remodelés par le projet.

| Fichier | Version | Utilisé pour |
|---|---|---|
| `upper-limb-obj.zip` (<https://caskanatomy.info/open3dmodelfiles/upper-limb/>), SHA-256 dans `pipeline/open3d.sha256` | juillet 2025 (fichier daté du 14/10/2026) | 50 objets nerveux du membre supérieur droit, et 18 os pour le recalage |

Seule la **géométrie** est utilisée : l'export OBJ n'a ni matériaux ni textures. Les textures des
exports Blender et glb (dérivées de « Thoracic walls », Claudia Krebs et al., UBC, CC BY-NC-SA 4.0)
ne sont ni téléchargées ni incluses.

## Modifications apportées

Faites par le projet Anatomo avec le code de `pipeline/` :

- sélection des structures (membre supérieur droit pour `upper_limb`, tout le corps pour `full_body`) ;
- regroupement des fichiers éléments par concept FMA ;
- recalage des maillages 3.0 dans le repère 4.0 : translation constante pour les os et muscles du
  membre supérieur, champ de déplacement mesuré sur les structures communes aux deux versions pour
  les structures propres à la 3.0 (`pipeline/anatomo_models/v3.py`) ;
- correction des paires droite/gauche placées du mauvais côté dans la source 4.0 (corps entier) ;
- fusion des sommets dupliqués, décimation ;
- changement de repère et d'unité (mm → m, axe vertical en +Y) ;
- fusion des maillages par système anatomique, avec un indice de structure par sommet ;
- reclassement explicite du système de quelques structures (disques intervertébraux, cartilages,
  tendons, ligaments, poils…), table `pipeline/anatomo_models/overrides.py` ;
- ajout de noms français (`data/fr_names.json`) et de repères osseux calculés (humérus) ;
- nerfs de l'Open3DModel (`upper_limb`) : recalage sur les os BodyParts3D par une similitude
  (rotation, translation, échelle uniforme d'environ 0,97), changement d'unité, regroupement des
  objets par concept FMA, rattachement à un identifiant FMA et à un nom français, fusion des
  sommets dupliqués, décimation (50 %).

`full_body` est distribué sous la licence de BodyParts3D, CC BY-SA 2.1 JP. `upper_limb`, qui contient
aussi les nerfs de l'Open3DModel, est distribué sous CC BY-SA 4.0, ce que permet l'article 5(2) de la
CC BY-SA 2.1 JP (version ultérieure de la même licence). Voir `LICENSE`.
Les fichiers glb portent l'attribution et l'URI de la licence dans `asset.copyright`, et les
manifestes et le fichier de repères dans leurs champs `attribution` et `license`.

## Pour les applications qui utilisent ces modèles

Afficher, pour chaque modèle affiché, son attribution (champ `attribution` du manifeste : BodyParts3D,
plus le crédit Open3DModel pour `upper_limb`), sa licence avec son lien (CC BY-SA 4.0 pour
`upper_limb`, CC BY-SA 2.1 JP pour `full_body`) et un lien vers ce dépôt, où les
modèles et le code qui les produit restent librement accessibles. Ne pas chiffrer ni verrouiller
les fichiers de modèles distribués.
