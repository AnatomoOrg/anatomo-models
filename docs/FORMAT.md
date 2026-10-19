# Format des modèles (`anatomo-models/1`)

Chaque modèle publié est un trio de fichiers : un `.glb` (glTF 2.0 binaire), un manifeste `.json` du même
nom et ses repères anatomiques `.landmarks.json`.

| Fichier | Contenu |
|---|---|
| `upper_limb.glb` / `.json` | Membre supérieur droit et ceinture scapulaire (MVP) : os, muscles, artères, veines, nerfs |
| `full_body.glb` / `.json` | Corps entier (contexte), tous systèmes, dont les nerfs des quatre membres, les sinus de la dure-mère et des nerfs du tronc |
| `<modèle>.landmarks.json` | Repères anatomiques : osseux, attaches musculaires, pouls, repères cliniques |

## Repère

Mètres, repère glTF : **+Y vers le haut**, **+Z vers l'avant** (face antérieure du sujet),
**+X vers la gauche du sujet**. Le membre supérieur droit est donc du côté des X négatifs.
Les deux modèles partagent le même repère : ils se superposent sans recalage, et les repères
osseux sont dans ce repère.

## Le glb : un maillage par système

Un nœud, un maillage et une seule primitive (triangles indexés, index `uint32`) par système
anatomique. L'ordre des nœuds suit l'ordre d'affichage : `os`, `muscles`, `arteres`, `veines`,
`nerfs`, `organes`, `peau` (les systèmes vides sont omis). Le nom du nœud est la clé du système.

### Systèmes

| Clé | Contenu |
|---|---|
| `os` | Os, cartilages costaux (partie des côtes dans la TA) et dents (tissu dur, montré avec le crâne dans les atlas) |
| `muscles` | Muscles squelettiques et leurs parties tendineuses : tendons, aponévroses, raphés (ligne blanche, raphé pharyngien), rétinaculums, anneau tendineux commun, tractus iliotibial |
| `arteres` | Artères |
| `veines` | Veines, sinus de la dure-mère (Z-Anatomy, `full_body`) |
| `nerfs` | Nerfs et ganglions (BodyParts3D n'a que des nerfs crâniens et orbitaires ; nerfs des membres : Open3DModel, membre supérieur dans `upper_limb`, membres supérieurs et inférieurs des deux côtés dans `full_body` ; dans `full_body`, nerfs du tronc de Z-Anatomy) |
| `organes` | Tout le reste : viscères, encéphale, cœur (y compris ses muscles papillaires), cartilages hors côtes (larynx, nez), disques intervertébraux, ligaments et membranes (sauf le ligament inguinal, partie de l'aponévrose de l'oblique externe, rangé en `muscles` comme la ligne blanche) |
| `peau` | Peau et phanères (cheveux, sourcils, poils pubiens) |

Le système vient du classement BodyParts3D/FMA (arbre is-a, noms anglais en secours). Les structures que ce
classement range mal sont corrigées par FMA ID dans `pipeline/anatomo_models/overrides.py`, avec la raison de
chaque correction ; le build applique cette table avant d'écrire les maillages, et échoue si une entrée ne
correspond plus à aucune structure.

Attributs de sommet :

| Attribut glTF | Nom three.js | Type | Sens |
|---|---|---|---|
| `POSITION` | `position` | `vec3` float | Position (m) |
| `NORMAL` | `normal` | `vec3` float | Normale lissée, par structure |
| `_STRUCTURE` | `_structure` | `float` | Indice de la structure dans le manifeste (entier exact) |
| `_FIBER` | `_fiber` | `vec3` byte normalisé | Direction des fibres musculaires (unitaire, tangente à la surface lissée, sans sens) ; `muscles` seulement, optionnel |
| `_TENDON` | `_tendon` | `float` (ubyte normalisé) | Masque tendon : 0 = charnu, 1 = tendon ; `muscles` seulement, optionnel |

### Fibres et tendons (`_FIBER`, `_TENDON`, optionnels)

Le maillage `muscles` peut porter deux attributs de plus, pour dessiner des fibres et des tendons procéduraux
sans texture ni UV (stries dans le sens de `_FIBER`, éclaircissement nacré là où `_TENDON` est élevé). Ils sont
optionnels et ajoutés sans changer le format : un lecteur qui les ignore lit le fichier comme avant, et l'app
doit rendre normalement un modèle qui ne les a pas (versions antérieures).

- `_FIBER` : accessor `VEC3`, `BYTE` normalisé (`normalized: true`, composante / 127), dans son propre
  bufferView avec `byteStride` 4 (un octet de bourrage par sommet). Vecteur unitaire à la quantification près ;
  son signe n'a pas de sens (une fibre n'a pas d'orientation).
- `_TENDON` : accessor `SCALAR`, `UNSIGNED_BYTE` normalisé (valeur / 255), bufferView avec `byteStride` 4.

Coût : 8 octets par sommet du maillage `muscles` (+1,7 Mo pour `upper_limb`, +2,7 Mo pour `full_body`).

Les deux sont calculés géométriquement par le pipeline (`pipeline/anatomo_models/fibers.py`), sur le maillage
publié de chaque structure :

- **direction** : champ qui court sur la surface de l'origine du muscle à son insertion. Les extrémités sont les
  repères `origine` et `insertion` du muscle quand il a les deux (les sommets autour d'eux, et ceux qui touchent un
  os près d'eux : une attache est une surface, pas un point), sinon les deux bouts de la structure le long de son
  axe principal (ACP), le plus étroit jouant l'insertion. Depuis chaque extrémité, une diffusion de chaleur sur la
  surface (Laplacien cotangent, méthode de la chaleur) donne la direction des géodésiques qui en partent ; la fibre
  suit leur différence, pondérée vers l'insertion. Le champ suit les muscles courbes et converge vers l'insertion
  des muscles en éventail (grand pectoral, deltoïde, grand dorsal). Il est moyenné sur environ 1 cm et tangent à
  la surface lissée (à quelques degrés près de `NORMAL`, qui suit le relief sculpté des maillages) ;
- **tendon** : parties de la structure nettement plus fines que son corps (épaisseur locale, mesurée là où la
  normale rentrante franchit l'axe médian) et de moins de 5 mm environ, dans les structures de plus de 5 à 9 cm
  (les petits muscles de la face, du cou profond ou du pied restent charnus). Les structures entièrement
  tendineuses (tendons, aponévroses, raphés, rétinaculums, ligne blanche, tractus iliotibial, ligament inguinal,
  anneau tendineux commun) valent 1 partout.

BodyParts3D ne sépare presque jamais le tendon du corps charnu : le masque est une estimation, à ne pas
présenter comme une limite anatomique.

Dans un maillage de système, les structures sont posées les unes après les autres (triées par
identifiant) : chacune occupe une plage **contiguë** de sommets et de triangles, et aucun sommet
n'est partagé entre deux structures. Chaque matériau porte une couleur indicative par système ;
l'app est censée appliquer ses propres matériaux.

`asset.copyright` contient l'attribution des sources avec l'URI de leurs licences ; `asset.extras`
contient `format`, `model`, `version` et `license` (`{id, url}`), la licence du modèle. Le glb ne
contient ni image, ni texture, ni coordonnées de texture.

## Licence de chaque modèle

| Modèle | `license.id` | Sources |
|---|---|---|
| `upper_limb` | `CC-BY-SA-4.0` | BodyParts3D (CC BY-SA 2.1 JP, adaptable sous une version ultérieure) et Open3DModel membre supérieur (CC BY-SA 4.0) pour les nerfs |
| `full_body` | `CC-BY-SA-4.0` | BodyParts3D, Open3DModel membres supérieur et inférieur (CC BY-SA 4.0) pour les nerfs des membres et Z-Anatomy (CC BY-SA 4.0) pour les sinus de la dure-mère et des nerfs du tronc (jusqu'à la 1.4.1 : `CC-BY-SA-2.1-JP`, BodyParts3D seul) |

L'app lit la licence et l'attribution dans le manifeste du modèle affiché (`license`, `attribution`),
sans les supposer identiques d'un modèle à l'autre.

## Le manifeste

```jsonc
{
  "format": "anatomo-models/1",
  "model": "upper_limb",
  "version": "1.0.0",
  "glb": "upper_limb.glb",
  "frame": {"units": "m", "up": "+Y", "anterior": "+Z", "subject_left": "+X"},
  "license": {"id": "CC-BY-SA-4.0", "url": "https://creativecommons.org/licenses/by-sa/4.0/"},
  "attribution": "BodyParts3D, © The Database Center for Life Science, … Nerves: \"Open3DModel - Upper limb …",
  "sources": [{"name": "BodyParts3D 4.0", "url": "…", "license": "CC-BY-SA-2.1-JP"}, …,
              {"name": "Open3DModel, upper limb (AnatomyTOOL), geometry only", "url": "…", "license": "CC-BY-SA-4.0"}],
  "systems": [
    {"key": "os", "node": "os", "vertices": 61234, "triangles": 120345, "structures": 32}
  ],
  "structures": [
    {
      "index": 0,                 // valeur de _STRUCTURE, unique dans le fichier
      "id": "FMA23130",           // FMA ID : clé stable entre versions, fiches, quiz, repères
      "en": "right humerus",      // nom FMA anglais (BodyParts3D)
      "fr": "Humérus",            // nom français, ou null si pas encore traduit
      "system": "os",
      "vertices": [0, 4210],      // [premier sommet, nombre] dans le maillage du système
      "triangles": [0, 8400],     // [premier triangle, nombre] dans le maillage du système
      "bbox": [[-0.21, 0.98, -0.05], [-0.15, 1.31, 0.02]],
      "source": "bodyparts3d-3.0"   // ou "bodyparts3d-4.0", "open3dmodel" (nerfs des membres)
    }
  ]
}
```

`source` vaut `bodyparts3d-4.0` ou `bodyparts3d-3.0` (os et muscles du membre supérieur, muscles absents de la
4.0 dans `full_body` : face, mastication, paroi abdominale, grand dorsal…), `open3dmodel` (nerfs des membres) ou
`z-anatomy` (sinus de la dure-mère, veines ophtalmiques et nerfs du tronc de `full_body`). Une
structure dont la géométrie vient de deux sources joint les deux par `+` : `bodyparts3d-4.0+z-anatomy` (veines
jugulaires internes : 4 cm de BodyParts3D prolongés jusqu'au foramen jugulaire par Z-Anatomy) et
`open3dmodel+z-anatomy` (troncs sympathiques : parties lombaire et sacrale de l'Open3DModel, cervicale et thoracique
de Z-Anatomy). Un lecteur qui teste la source doit donc chercher un des noms dans la valeur, pas l'égalité.

`index` est propre à un fichier et peut changer d'une version à l'autre : l'app ne doit stocker
que `id` (FMA ID). Dans `full_body`, quelques structures sans concept FMA gardent l'identifiant
de leur fichier élément BodyParts3D (`FJ…`).

Les nerfs Open3DModel portent aussi un FMA ID, choisi à la main. Un objet source qui regroupe plusieurs
nerfs (divisions du plexus brachial, nerfs digitaux, nerfs cluniaux…) est rattaché au concept FMA d'ensemble
ou générique, qui n'a pas de côté dans la FMA :

- dans `upper_limb`, son nom anglais est celui de la FMA, sans côté (`set of anterior divisions of brachial
  plexus`, `proper palmar digital branch of median nerve`…) : le côté est celui du modèle (droit) ;
- dans `full_body`, qui a les deux côtés, le nom anglais porte le côté (`set of anterior divisions of right
  brachial plexus`, `… of left brachial plexus`), comme tous les autres nerfs. Le côté droit garde le FMA ID du
  concept générique (le même que dans `upper_limb`) ; le côté gauche prend ce FMA ID suivi de **`-L`**
  (`FMA77549-L`), seul cas d'identifiant qui n'est ni un FMA ID ni un fichier `FJ…`. Les ensembles de Z-Anatomy
  suivent la même règle : `FMA75467` / `FMA75467-L` (nerfs intercostaux droits / gauches), `FMA75599` /
  `FMA75599-L` (rameaux communicants des troncs sympathiques). Une structure gauche
  se relie à son homologue droite par le nom anglais (`left` → `right`), comme les autres structures paires.

## Repères anatomiques

```jsonc
{
  "format": "anatomo-models/1", "model": "full_body", "version": "1.1.0", "frame": { … },
  "license": { … }, "attribution": "…",
  "landmarks": [
    {"id": "humerus.tete", "structure": "FMA23130", "side": "right", "fr": "Tête de l'humérus",
     "kind": "articulaire", "position": [-0.17, 1.30, -0.01]},
    {"id": "biceps-brachial-long.origine", "structure": "FMA37686", "side": "right",
     "fr": "Tubercule supraglénoïdal", "kind": "origine", "position": [ … ]},
    {"id": "manubrium.incisure-jugulaire", "structure": "FMA7486", "side": null, … }
  ]
}
```

- `id` (`<structure>.<repère>`, ASCII) est stable d'une version à l'autre et **ne porte pas le côté** : les fiches
  et les quiz s'y réfèrent. Un repère d'une structure paire existe une fois par côté : la clé unique d'un repère
  dans un fichier est le couple (`id`, `side`).
- `structure` est le FMA ID de la structure qui porte le repère (celle du côté du repère).
- `side` vaut `right`, `left`, ou `null` pour un repère médian (incisure jugulaire, processus épineux…). Une
  structure médiane peut porter des repères pairs (processus transverses, incisures claviculaires du manubrium) :
  `side` est alors renseigné et le côté droit est en X négatif.
- `kind` :

  | `kind` | Porté par | Sens |
  |---|---|---|
  | `saillie` | os (ou cartilage du larynx) | Processus, tubercule, épine, épicondyle… |
  | `articulaire` | os | Surface articulaire (tête, condyle, cavité) |
  | `depression` | os | Fosse, sillon, incisure |
  | `repere` | os | Autre repère (col, bord, repère de niveau ou de nerf) |
  | `origine` | muscle | Attache d'origine ; `fr` nomme le site osseux |
  | `insertion` | muscle | Attache terminale ; `fr` nomme le site osseux |
  | `pouls` | artère | Point de prise du pouls |
  | `clinique` | vaisseau, organe | Voie d'abord, ponction, point clinique (McBurney…) |

- `position` est sur la surface publiée de la structure, décalée de 1,5 mm vers l'extérieur, dans le repère du
  modèle.

Les positions sont **calculées géométriquement**, pas placées par un anatomiste : point extrême dans une direction
anatomique, fond d'une fosse, centre d'une surface, partie d'un muscle au contact de son os, point d'une artère le
plus proche d'un os ou d'un autre repère. Les règles, structure par structure, sont dans
`pipeline/anatomo_models/landmark_catalog.py` ; elles tournent sur les maillages pleine résolution, puis le point est
ramené sur la surface publiée. Toutes les positions restent à faire valider. Une attache dont le muscle n'atteint
pas l'os dans le modèle (chef qui se termine sur un tendon commun) est omise ; si l'os manque au modèle (pas de côtes
ni de sternum dans `upper_limb`), le repère est placé à l'extrémité correspondante du muscle.

Les repères liés aux nerfs sont portés par les os (sillon du nerf ulnaire, col de la fibula) : BodyParts3D n'a pas
les nerfs périphériques, et les nerfs Open3DModel n'ont pas encore de repères.

Jusqu'à la v1.0.0, seul `upper_limb` avait des repères (12, sur l'humérus) et ils n'avaient pas de `side`.

## Utilisation côté app (three.js)

- **Sélection** : `raycaster.intersectObject(systemMesh)` donne `hit.face.a` ; la structure est
  `geometry.attributes._structure.getX(hit.face.a)`, à relier au manifeste par `index`.
  Alternative sans attribut : recherche dichotomique de `hit.faceIndex` dans les plages `triangles`.
- **Surbrillance, masquage, couleur par structure** : une `DataTexture` (une texel par structure)
  lue dans le shader via `_structure` ; un changement d'état = une écriture dans la texture,
  sans reconstruire la géométrie.
- **Transparence (fantôme)** : dessiner le maillage du système deux fois, une passe opaque qui
  écarte (`discard`) les structures fantômes, puis une passe transparente qui ne garde qu'elles.
- **Masquer beaucoup de structures** : `geometry.setDrawRange` ou des groupes construits à partir
  des plages `triangles`, puisque les structures sont contiguës.
- **Cadrage sur une structure** : `bbox`.
- **Fibres** : si `geometry.attributes._fiber` existe, three.js le lit normalisé (`vec3` dans [-1, 1]) et
  `_tendon` comme un `float` dans [0, 1] ; les positions sont en mètres dans l'espace objet, ce qui fixe la
  fréquence d'un bruit procédural.
