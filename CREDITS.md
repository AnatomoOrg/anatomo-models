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

## Open3DModel (nerfs des membres)

Les **nerfs des membres** des modèles `upper_limb` (membre supérieur droit) et `full_body` (membres
supérieurs et inférieurs, des deux côtés) viennent de l'**Open3DModel**, projet « Open 3D Anatomical
Model for Education » (Leiden University Medical Center, Radboud UMC et autres, publié sur
AnatomyTOOL), licence [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
Crédit demandé par AnatomyTOOL pour le membre supérieur (<https://anatomytool.org/node/63906>) :

> "Open3DModel - Upper limb - English labels" at AnatomyTOOL.org by Open3D project, Jan Kooloos,
> RadboudUMC, Eungyeol Lee, LUMC et al, license: Creative Commons Attribution-ShareAlike

Contenu anatomique du membre supérieur : Jan (J.) Kooloos, PhD, anatomist em., Radboud University Nijmegen, dept. Anatomy ;
prof. Marco (M.C.) DeRuiter, PhD, Leiden University Medical Center (LUMC), dept. Anatomy & Embryology ;
Denise (D.M.J.) Arnold, MD, University of Toronto (vaisseaux et nerfs) ; Prof. em. George J.R. Maat,
MD, PhD, LUMC (os et articulations). Modélisation 3D : Eungyeol Lee, BFA, MSI, LUMC. Modèle web :
Daniël Jansma, MSc, LUMC. L'Open3DModel s'appuie sur BodyParts3D et Z-Anatomy (CC BY-SA 4.0) ; ses
nerfs du membre supérieur ont été entièrement remodelés par le projet.

| Fichier | Version | Utilisé pour |
|---|---|---|
| `upper-limb-obj.zip` (<https://caskanatomy.info/open3dmodelfiles/upper-limb/>), SHA-256 dans `pipeline/open3d.sha256` | juillet 2025 (fichier daté du 14/10/2026) | 50 objets nerveux du membre supérieur droit, et 18 os pour le recalage |
| `lower-limb-obj.zip` (<https://caskanatomy.info/open3dmodelfiles/lower-limb/>), SHA-256 dans `pipeline/open3d.sha256` | juillet 2025 (fichier daté du 14/10/2026) | 65 objets nerveux du membre inférieur droit (racines L1–S5, plexus lombaire et sacral, nerfs du membre inférieur), et 24 os pour le recalage (`full_body` seulement) |

Crédit demandé par AnatomyTOOL pour le membre inférieur (<https://anatomytool.org/node/63936>, licence
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)) :

> "Open3DModel - Lower limb - English labels" at AnatomyTOOL.org by Open3D project, Jan Kooloos,
> RadboudUMC, Eungyeol Lee, LUMC et al, license: Creative Commons Attribution-ShareAlike

Contenu anatomique du membre inférieur : Jan (J.) Kooloos, PhD, Radboud University Nijmegen (muscles) ;
Prof. dr. Evie (E.) Vereecke, PhD, KU Leuven Campus Kulak (relecture des muscles) ; Eungyeol Lee, BFA, MSI,
LUMC (nerfs et vaisseaux) ; Prof. em. Koos-Jaap (K.J.) van Zwieten, PhD, Hasselt University (relecture des nerfs
et vaisseaux) ; Prof. em. George J.R. Maat, MD, PhD, LUMC (os et articulations). Modélisation 3D : Eungyeol Lee.
Modèle web : Daniël Jansma, MSc, LUMC. Contributions : Emily (E.C.A.) Lowes, MSc.

Seule la **géométrie** est utilisée : les exports OBJ n'ont ni matériaux ni textures. Les textures des
exports Blender et glb (dérivées de « Thoracic walls », Claudia Krebs et al., UBC, CC BY-NC-SA 4.0)
ne sont ni téléchargées ni incluses.

## Z-Anatomy (sinus de la dure-mère, nerfs du tronc ; `full_body`)

Les **sinus veineux de la dure-mère**, les **veines ophtalmiques**, la partie haute des **veines jugulaires
internes** et des **nerfs du tronc** de `full_body` viennent de **Z-Anatomy**
(Gauthier Kervyn, <https://www.z-anatomy.com/>), dépôt <https://github.com/Z-Anatomy/Models-of-human-anatomy>,
licence [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Le README du dépôt dit :

> All the code and content shared by ‘Z-Anatomy’ is under Creative Commons Attribution-ShareAlike 4.0 International License.

et demande le crédit :

> ”Z-Anatomy - The libre 3D atlas of anatomy - CC-BY-SA 4.0”

Z-Anatomy dérive lui-même de BodyParts3D (« It includes models derived from 'BodyParts3D' »).

| Fichier | Version | Utilisé pour |
|---|---|---|
| `Z-Anatomy.zip` (<https://github.com/Z-Anatomy/Models-of-human-anatomy>, commit `767f14e0a4dfc55aa7c3455685b62339a4faec99`), SHA-256 dans `pipeline/zanatomy.sha256` | `Startup.blend` daté du 02/05/2023 (Blender 3.5) | 31 objets en liste blanche (29 structures, dont 4 complètent une structure existante) et 56 os pour le recalage |

**Provenance objet par objet.** Le README de Z-Anatomy cite des modèles tiers « used as reference/included and
adapted », dont deux **non commerciaux** : « Anatomy of the Inner Ear - by University of Dundee School of Medicine -
CC-BY-NC-SA 4.0 » et « Kidney - by Lissie Cowley - CC-BY-NC 4.0 » ; « Brainder » et « White matter » (University of
Washington) n'ont pas de licence indiquée. « Cranial Nerves and Foramina - by University of Dundee, CAHID » est
CC BY 4.0 selon le README seulement : sa page (Sophia Lappe, 2021,
<https://sketchfab.com/3d-models/cranial-nerves-and-foramina-a9358ee7a6dd4ea18a3622114405a4c7>) n'affiche aucune
licence Creative Commons, n'est pas téléchargeable et porte l'étiquette « NoAI ». Les nerfs crâniens de Z-Anatomy
en sont peut-être adaptés : leur provenance n'est pas établie, **aucun nerf crânien de Z-Anatomy n'est lu**.
Z-Anatomy ne marque pas la provenance de chaque objet. Le pipeline ne lit donc qu'une **liste blanche explicite**
(`OBJECTS` dans `pipeline/anatomo_models/zanatomy.py`) :

- des **courbes** Blender (splines de Bézier à biseau rond, tracées dans Blender, pas l'import d'un maillage tiers) :
  sinus, veines ophtalmiques, veine jugulaire interne, nerfs intercostaux, troncs sympathiques et rameaux
  communicants. Aucune ne se trouve dans l'oreille, le rein ou l'encéphale, ni n'est un nerf crânien ;
- trois **maillages** absents de BodyParts3D et de tous les modèles tiers cités, donc propres à Z-Anatomy : sinus
  caverneux, plexus basilaire, ganglions des troncs sympathiques.

Sont exclus, en plus de tout ce qui touche l'oreille, le rein et l'encéphale (surfaces, noyaux, tractus) : **tous
les nerfs crâniens** et leurs branches (olfactif, optique, oculomoteur, trochléaire, trijumeau et ses branches,
abducens, glossopharyngien, vague, accessoire, hypoglosse ; voir ci-dessus), et en particulier le
**nerf facial**, la **corde du tympan** et le **nerf vestibulocochléaire** (nerfs cochléaire et vestibulaire), que
le modèle non commercial de l'oreille interne de Dundee contient (<https://anatomytool.org/node/60505>). Le build
refuse de lire un objet hors liste ou dont le nom touche ces régions. Seule la géométrie est lue (le `.blend` n'a
pas de texture) ; le module Python du zip n'est ni extrait ni exécuté.

Le zip n'est pas republié avec les releases (il contient aussi les parties non commerciales) : son URL est
versionnée par le commit, et `pipeline/fetch_zanatomy.sh` accepte un miroir privé (`ZANATOMY_MIRROR`).

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
  sommets dupliqués, décimation (50 %) ;
- nerfs de l'Open3DModel (`full_body`, membres supérieur et inférieur) : côté gauche obtenu par symétrie
  du côté droit ; recalage de chaque côté sur les os BodyParts3D 4.0 du corps entier (similitude, puis
  recalage rigide os par os et champ de déplacement interpolé depuis les os) ; nerfs cutanés qui dépassaient
  de la peau BodyParts3D repoussés sous la peau ; rattachement à un identifiant FMA par côté et à un nom
  français ; décimation (25 %) ;
- structures de Z-Anatomy (`full_body`) : lecture du `.blend` sans Blender, courbes balayées en tubes ronds,
  recalage sur les os BodyParts3D 4.0 (similitude, puis recalage rigide os par os et champ de déplacement), correction
  de la position du sinus droit et du sinus occipital (décalage de parent de 44,5 mm dans la source), raccord de la
  veine jugulaire interne au sinus sigmoïde (7 mm) et du tronc sympathique thoracique au tronc lombaire de
  l'Open3DModel, parties qui doublent une structure BodyParts3D retirées,
  rattachement à un identifiant FMA et à un nom français ;
- attributs de sommet `_FIBER` (direction des fibres) et `_TENDON` (zones tendineuses) ajoutés au
  maillage `muscles`, calculés depuis les repères d'origine et d'insertion ou l'axe du muscle.

`upper_limb` et `full_body`, qui contiennent aussi des nerfs de l'Open3DModel (et, pour `full_body`, des
structures de Z-Anatomy, CC BY-SA 4.0), sont distribués sous CC BY-SA 4.0, ce que permet l'article 5(2) de la CC BY-SA 2.1 JP (version ultérieure de la même licence).
Jusqu'à la version 1.4.1, `full_body` (BodyParts3D seul) était distribué sous CC BY-SA 2.1 JP. Voir `LICENSE`.
Les fichiers glb portent l'attribution et l'URI de la licence dans `asset.copyright`, et les
manifestes et le fichier de repères dans leurs champs `attribution` et `license`.

## Pour les applications qui utilisent ces modèles

Afficher, pour chaque modèle affiché, son attribution (champ `attribution` du manifeste : BodyParts3D,
plus le crédit Open3DModel du membre supérieur pour `upper_limb`, des membres supérieur et inférieur et le
crédit Z-Anatomy pour `full_body`), sa licence avec son lien (CC BY-SA 4.0 pour les deux modèles) et un lien vers ce dépôt, où les
modèles et le code qui les produit restent librement accessibles. Ne pas chiffrer ni verrouiller
les fichiers de modèles distribués.
