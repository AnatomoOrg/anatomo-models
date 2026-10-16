# Format des modèles (`anatomo-models/1`)

Chaque modèle publié est une paire de fichiers : un `.glb` (glTF 2.0 binaire) et un manifeste `.json`
du même nom. Le membre supérieur a en plus un fichier de repères osseux.

| Fichier | Contenu |
|---|---|
| `upper_limb.glb` / `.json` | Membre supérieur droit (MVP) : os, muscles, artères, veines |
| `upper_limb.landmarks.json` | Repères osseux de l'humérus |
| `full_body.glb` / `.json` | Corps entier (contexte), tous systèmes |

## Repère

Mètres, repère glTF : **+Y vers le haut**, **+Z vers l'avant** (face antérieure du sujet),
**+X vers la gauche du sujet**. Le membre supérieur droit est donc du côté des X négatifs.
Les deux modèles partagent le même repère : ils se superposent sans recalage, et les repères
osseux sont dans ce repère.

## Le glb : un maillage par système

Un nœud, un maillage et une seule primitive (triangles indexés, index `uint32`) par système
anatomique. L'ordre des nœuds suit l'ordre d'affichage : `os`, `muscles`, `arteres`, `veines`,
`nerfs`, `organes`, `peau` (les systèmes vides sont omis). Le nom du nœud est la clé du système.

Attributs de sommet :

| Attribut glTF | Nom three.js | Type | Sens |
|---|---|---|---|
| `POSITION` | `position` | `vec3` float | Position (m) |
| `NORMAL` | `normal` | `vec3` float | Normale lissée, par structure |
| `_STRUCTURE` | `_structure` | `float` | Indice de la structure dans le manifeste (entier exact) |

Dans un maillage de système, les structures sont posées les unes après les autres (triées par
identifiant) : chacune occupe une plage **contiguë** de sommets et de triangles, et aucun sommet
n'est partagé entre deux structures. Chaque matériau porte une couleur indicative par système ;
l'app est censée appliquer ses propres matériaux.

`asset.copyright` contient l'attribution BodyParts3D avec l'URI de la licence ; `asset.extras`
contient `format`, `model`, `version` et `license` (`{id, url}`).

## Le manifeste

```jsonc
{
  "format": "anatomo-models/1",
  "model": "upper_limb",
  "version": "1.0.0",
  "glb": "upper_limb.glb",
  "frame": {"units": "m", "up": "+Y", "anterior": "+Z", "subject_left": "+X"},
  "license": {"id": "CC-BY-SA-2.1-JP", "url": "https://creativecommons.org/licenses/by-sa/2.1/jp/"},
  "attribution": "BodyParts3D, © The Database Center for Life Science, …",
  "sources": [{"name": "BodyParts3D 4.0", "url": "…", "license": "CC-BY-SA-2.1-JP"}],
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
      "source": "bodyparts3d-3.0"
    }
  ]
}
```

`index` est propre à un fichier et peut changer d'une version à l'autre : l'app ne doit stocker
que `id` (FMA ID). Dans `full_body`, quelques structures sans concept FMA gardent l'identifiant
de leur fichier élément BodyParts3D (`FJ…`).

## Repères osseux

```jsonc
{
  "format": "anatomo-models/1", "version": "1.0.0", "frame": { … },
  "license": { … }, "attribution": "…",
  "landmarks": [
    {"id": "humerus.tete", "structure": "FMA23130", "fr": "Tête de l'humérus",
     "kind": "articulaire", "position": [-0.17, 1.30, -0.01]}
  ]
}
```

`kind` vaut `saillie`, `articulaire`, `depression` ou `repere`. Les identifiants `humerus.<slug>`
sont stables. Les positions sont calculées géométriquement (sommet extrême dans une direction
anatomique) et décalées de 1,5 mm vers l'extérieur ; elles restent à faire valider.

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
