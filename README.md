# anatomo-models

Modèles 3D anatomiques de l'app Anatomo, et le pipeline qui les produit à partir de
[BodyParts3D](https://dbarchive.biosciencedbc.jp/en/bodyparts3d/) et, pour les nerfs des membres,
de l'Open3DModel (AnatomyTOOL : [membre supérieur](https://anatomytool.org/node/63906),
[membre inférieur](https://anatomytool.org/node/63936)) et, pour les sinus de la dure-mère, des nerfs crâniens et
des nerfs du tronc du corps entier, de [Z-Anatomy](https://github.com/Z-Anatomy/Models-of-human-anatomy).

Les modèles sont des œuvres dérivées publiées en libre accès sous **CC BY-SA 4.0** : ils combinent
BodyParts3D (CC BY-SA 2.1 Japon, adaptable sous une version ultérieure), les nerfs de l'Open3DModel
(CC BY-SA 4.0) et une liste blanche d'objets de Z-Anatomy (CC BY-SA 4.0). Le code du pipeline est sous licence MIT.
Voir [`LICENSE`](LICENSE) et [`CREDITS.md`](CREDITS.md).

## Télécharger les modèles

Les fichiers `.glb` ne sont pas versionnés dans git : ils sont attachés aux
[Releases](https://github.com/AnatomoOrg/anatomo-models/releases) (`v<VERSION>`), avec leurs
manifestes, leurs repères anatomiques, une somme SHA-256 et les textes de licence.

| Modèle | Contenu | Maillages (draw calls) |
|---|---|---|
| `upper_limb` | Membre supérieur droit et ceinture scapulaire (MVP) : os, muscles, artères, veines, nerfs | 5 |
| `full_body` | Corps entier, tous systèmes (contexte), dont les nerfs des quatre membres, les sinus de la dure-mère, des nerfs crâniens et des nerfs du tronc | 7 |

Chaque modèle a **un maillage par système** au lieu d'un maillage par structure (le prototype
en avait 2 234 pour le corps entier), et garde la sélection structure par structure grâce à un
indice de structure par sommet. Le format est décrit dans [`docs/FORMAT.md`](docs/FORMAT.md).

## Construire

```sh
pip install -r pipeline/requirements.txt
pipeline/fetch_bp3d.sh bp3d                 # ~750 Mo, sommes SHA-256 vérifiées
pipeline/fetch_open3d.sh bp3d/open3d        # nerfs des membres, OBJ ~21 + 20 Mo, géométrie seule
pipeline/fetch_zanatomy.sh bp3d/zanatomy    # sinus et nerfs (full_body), zip 87 Mo, Startup.blend 307 Mo
python pipeline/build.py bp3d build         # ou --only upper_limb / --only full_body
python pipeline/check.py build/upper_limb.json build/full_body.json
python -m pytest -q tests
```

## Publier une version

Changer `VERSION` sur `main`. Le workflow `Release models` reconstruit les modèles depuis les
sources, les vérifie (cohérence glb ↔ manifeste, validateur glTF Khronos) et crée la release
`v<VERSION>`. Une release existante n'est jamais écrasée.

### Source Open3DModel : miroir et changement en amont

Les URL d'AnatomyTOOL ne sont pas versionnées : les fichiers `upper-limb-obj.zip` et `lower-limb-obj.zip`
y sont remplacés sur place (dernières versions datées du 14/10/2026). Ils sont épinglés par leur somme
SHA-256 (`pipeline/open3d.sha256`), et chaque release publie, tels quels, les zips qui ont servi au build
(assets `upper-limb-obj.zip` et `lower-limb-obj.zip`, avec leur somme dans `SHA256SUMS`).
`pipeline/fetch_open3d.sh` essaie dans l'ordre, pour chacun, sans jeton :

1. `$OPEN3D_MIRROR/<fichier>` si la variable est définie, par exemple
   `OPEN3D_MIRROR=https://github.com/AnatomoOrg/anatomo-models/releases/download/v1.3.0` pour
   reconstruire exactement une release ;
2. l'asset de la dernière release du dépôt (`releases/latest/download/<fichier>`) ;
3. l'URL amont.

Un fichier dont la somme diffère de la somme épinglée est écarté, quelle que soit sa provenance. La
première release qui publie le miroir (1.3.0 pour le membre supérieur, la suivante pour le membre
inférieur) se construit depuis l'URL amont.

Si aucune source n'a la somme épinglée (fichier modifié en amont alors que l'ancienne version n'est
plus servie, ou nouvelle version à adopter), le build s'arrête : rien n'est publié avec un fichier non
relu. Pour adopter la nouvelle version :

1. Relire la licence et le crédit demandés sur <https://anatomytool.org/node/63906> (membre supérieur),
   <https://anatomytool.org/node/63936> (membre inférieur) et <https://anatomytool.org/node/63903>
   (toujours CC BY-SA 4.0, export OBJ sans texture) ; reporter un changement de crédit dans
   `pipeline/anatomo_models/open3d.py` ou `open3d_lower.py` (`CREDIT`) et `CREDITS.md`.
2. Télécharger le zip amont, vérifier qu'il ne contient que des `.obj` (`unzip -l`), calculer sa somme
   (`sha256sum`) et la mettre dans `pipeline/open3d.sha256`. Le miroir de la dernière release, qui a
   l'ancienne somme, sera alors écarté et l'URL amont utilisée.
3. `pipeline/fetch_open3d.sh bp3d/open3d && python pipeline/build.py bp3d build` : le build échoue si un
   objet de `NERVES` ou un os de `BONES` a disparu ou a été renommé (adapter la table), ou si le recalage
   dépasse 4 mm RMS (5,5 mm pour un os seul dans `full_body`). Contrôler le journal du recalage, le nombre
   de nerfs et ceux repoussés sous la peau.
4. `python pipeline/check.py …`, `python -m pytest -q tests`, puis mettre à jour la date du fichier
   dans `CREDITS.md`. La release suivante publiera le nouveau zip comme miroir.

Aucune copie binaire n'est gardée dans git.

## Sources et choix du pipeline

- **Os et muscles du membre supérieur** : BodyParts3D 3.0, maillages « 95 % » (environ cinq fois
  plus denses que la 4.0), recalés dans le repère de la 4.0 par une translation constante
  (0,7 ; −3,7 ; −10,3 mm). La clavicule et la scapula diffèrent de quelques millimètres.
- **Vaisseaux et corps entier** : BodyParts3D 4.0, maillages « 99 % ».
- **Muscles absents de la 4.0** (face, mastication, paroi abdominale, grand dorsal, carré des lombes,
  multifide, court extenseur des orteils…) : maillages 3.0 entiers, listés à la main dans
  `V3_ADDITIONS` (`pipeline/full_body.py`, `pipeline/upper_limb.py`). Le corps 3.0 n'est pas une copie
  rigide du corps 4.0 : la translation constante du bras est fausse de 8 mm à l'atlas et au bassin, de
  40 mm au pied. Ces maillages sont donc recalés par un champ de déplacement mesuré sur les 485
  structures présentes dans les deux versions (`pipeline/anatomo_models/v3.py`) : erreur médiane
  estimée 1,1 mm, 90 % sous 5 mm. Les autres concepts propres à la 3.0 doublent une géométrie 4.0
  (chefs du fléchisseur superficiel des doigts, ventres du digastrique, cheveux, ténias…) et sont
  écartés.
- **Nerfs du membre supérieur** : Open3DModel (export OBJ « upper limb », géométrie seule, SHA-256
  épinglé ; les textures, CC BY-NC-SA, ne sont jamais téléchargées). 50 objets nerveux, du plexus
  brachial (rameaux antérieurs C5–T1, troncs, divisions, faisceaux) aux nerfs digitaux, rattachés à
  48 concepts FMA par une table manuelle (`pipeline/anatomo_models/open3d.py`). L'Open3DModel est
  environ 3 % plus grand que BodyParts3D et décalé d'une dizaine de centimètres : le build le recale
  sur les os BodyParts3D du modèle par une similitude (ICP sur 18 os communs : scapula, clavicule,
  humérus, radius, ulna, carpe, métacarpiens ; erreur résiduelle 1,3 mm RMS) et échoue si le recalage
  dépasse 4 mm. Décimation 50 % (environ 99 000 triangles pour les nerfs).
- **Nerfs des membres dans `full_body`** (1 954 structures dont 253 nerfs, au lieu de 33 nerfs crâniens et
  orbitaires) : les 48 nerfs du membre supérieur ci-dessus et 62 concepts du membre inférieur de
  l'Open3DModel (export OBJ « lower limb », 65 objets : racines L1–S5, plexus lombaire et sacral, tronc
  sympathique lombo-sacral, nerfs sciatique, fémoral, obturateur, tibial, fibulaires, glutéaux, pudendal,
  cutanés, cluniaux, plantaires, digitaux ; table `pipeline/anatomo_models/open3d_lower.py`), chacun des
  deux côtés : 220 nerfs, environ 300 000 triangles (décimation 25 %), +8 Mo pour le glb. L'Open3DModel
  n'ayant que le côté droit, le gauche est obtenu par symétrie puis recalé sur les os gauches
  (`pipeline/anatomo_models/open3d_full_body.py`). Chaque côté est recalé sur les os 4.0 du corps entier
  par une similitude, puis os par os (ICP rigide), les nerfs suivant un champ de déplacement interpolé depuis
  les os : erreur résiduelle 1,8 mm RMS sur les 18 os du membre supérieur, 2,6 mm sur les 24 os du membre
  inférieur (rachis lombaire, sacrum, os coxal, os longs, tarse, métatarse ; une similitude seule laissait
  6 mm, l'Open3DModel ayant un tibia 2 cm plus court et une autre posture de hanche). Les nerfs cutanés qui
  dépassaient de la peau BodyParts3D (jusqu'à 10 mm : nerfs cluniaux, cutané latéral de la cuisse, rameau
  cutané du nerf obturateur…) sont repoussés à 2,5 mm sous sa surface (`pipeline/anatomo_models/skin.py`).
  Le côté gauche prend les concepts FMA gauches ; voir [`docs/FORMAT.md`](docs/FORMAT.md#le-manifeste) pour
  les concepts sans côté.
- **Sinus de la dure-mère, nerfs crâniens et nerfs du tronc dans `full_body`** : Z-Anatomy (`Startup.blend` du
  commit `767f14e`, SHA-256 épinglé, lu sans Blender par `pipeline/anatomo_models/blend.py` ; seule une liste blanche
  d'objets est lue, voir [`CREDITS.md`](CREDITS.md#z-anatomy-sinus-de-la-dure-mère-nerfs-crâniens-nerfs-du-tronc--full_body)) :
  sinus sagittaux supérieur et inférieur, droit, occipital, transverses, sigmoïdes, pétreux supérieurs et inférieurs,
  caverneux, intercaverneux, plexus basilaire, veines ophtalmiques, partie haute des veines jugulaires internes
  (du foramen jugulaire aux 4 cm de BodyParts3D) ; nerfs olfactif, oculomoteur, trijumeau (avec les nerfs maxillaire,
  troncs du nerf mandibulaire, nerfs buccal, lingual, alvéolaire inférieur, mylohyoïdien et mentonnier), abducens,
  glossopharyngien, vague (partie cervicale), accessoire et hypoglosse ; nerfs intercostaux, troncs sympathiques
  cervical et thoracique (raccordés au tronc lombo-sacral de l'Open3DModel) et rameaux communicants. Z-Anatomy dessine
  vaisseaux et nerfs en courbes : elles sont balayées en tubes ronds (6 à 12 côtés, une section tous les 1,5 mm), sans
  décimation. Z-Anatomy est un BodyParts3D remis à l'échelle (environ 1,02) et déplacé : recalage sur 56 os 4.0 du
  corps entier (crâne, maxillaires, vertèbres C1–L2, sternum, côtes) par une similitude puis os par os, comme
  l'Open3DModel (erreur résiduelle 2,1 mm RMS ; os du crâne 1,3 à 2,9 mm). `full_body` : 57 structures de plus,
  et 4 structures existantes complétées.
- Fusion des sommets dupliqués avant décimation (sinon la décimation ouvre des trous), puis
  décimation : 20 % pour le membre supérieur (minimum 3 000 triangles par structure, environ
  610 000 hors nerfs, 708 000 avec les nerfs) ; pour le corps entier, 20 % (minimum 200 triangles)
  sauf les artères, veines et nerfs BodyParts3D, gardés à 25 % (minimum 600 triangles) parce qu'à
  200 triangles les petites artères perdaient jusqu'à 3 mm de leur extrémité et les gros troncs devenaient
  anguleux : environ 1,75 M triangles hors nerfs des membres (2,05 M avec).
- Chaque fichier élément de BodyParts3D est rattaché à son concept FMA le plus spécifique (dans
  les arbres is-a et part-of).
- Le build échoue si les maillages 3.0 manquent (pas de repli silencieux sur la 4.0) ; un concept
  dont une partie des fichiers est prise par un concept plus précis reste en 4.0, pour ne pas
  dessiner deux fois la même géométrie.
- BodyParts3D 4.0 place quelques structures du mauvais côté (court fléchisseur du pouce,
  constricteur moyen du pharynx, bras du colliculus supérieur, veine lombaire ascendante) : dans
  le corps entier, le pipeline échange les deux maillages quand une paire droite/gauche est
  entièrement du mauvais côté, et l'indique dans le journal du build.

## Limites connues

- BodyParts3D n'a **pas de nerfs des membres** : ceux de `upper_limb` et `full_body` viennent de
  l'Open3DModel, un autre sujet recalé sur nos os. Après recalage, quelques nerfs touchent encore
  un os de quelques millimètres (nerf radial dans le sillon du nerf radial, jusqu'à 5,6 mm ; nerf
  cutané latéral inférieur du bras, nerf suprascapulaire, jusqu'à 3,3 mm). Les nerfs digitaux suivent
  la position des doigts de l'Open3DModel, proche de la nôtre. Le nerf thoracodorsal et le nerf
  intercostobrachial manquent (absents de la source). Points anatomiques incertains : voir
  [`docs/NOMS.md`](docs/NOMS.md#nerfs-du-membre-supérieur-open3dmodel).
- **Nerfs de `full_body`** : mêmes limites, plus celles du recalage sur les os 4.0. Après recalage, les racines
  sacrales et coccygiennes traversent le sacrum BodyParts3D, dont le canal sacral n'est pas modélisé (20 à 35 %
  de leurs sommets dans l'os) ; le nerf subscapulaire inférieur touche la 5e côte (le gril costal de
  BodyParts3D est plus près de la scapula) ; quelques nerfs digitaux entrent dans les phalanges (position des
  doigts et des orteils de la source). Les nerfs cutanés repoussés sous la peau gardent leur forme mais pas
  leur trajet exact. Il manque encore, dans le tronc, les nerfs phréniques, le plexus cervical, les nerfs
  splanchniques, le nerf subcostal, les parties thoracique et abdominale du nerf vague (absents de Z-Anatomy ou
  inutilisables, voir ci-dessous) et la moelle spinale. Noms et points incertains du membre inférieur :
  [`docs/NOMS.md`](docs/NOMS.md#nerfs-du-membre-inférieur-open3dmodel-full_body).
- Le grand dorsal et le chef profond du court fléchisseur du pouce (dont le fichier 4.0 est du mauvais
  côté) viennent de la 3.0 seule, recalés par le champ de déplacement, comme les trois parties du
  trapèze (qui atteignent le rachis et l'occiput, où la translation constante du bras est fausse de
  plusieurs millimètres) : leur position est moins sûre que celle des autres structures du membre
  supérieur, recalées par la translation constante.
- **Peau** (`full_body`) : le maillage BodyParts3D est une coque fermée d'environ 2 mm d'épaisseur
  (surfaces externe et interne raccordées aux orifices). Les fentes palpébrales sont ouvertes, comme sur
  un sujet aux yeux ouverts : la cornée est visible entre les paupières, ce n'est pas un trou. Quelques
  structures dépassent la peau de quelques millimètres, parce que les maillages sources ne sont pas
  ajustés entre eux : cartilages du nez (2 à 5 mm), auricule (`external ear`), quelques veines
  superficielles des doigts, et certains muscles ajoutés depuis la 3.0 (partie orbitaire de
  l'orbiculaire de l'œil, temporo-pariétal). Les cheveux, sourcils et poils
  pubiens, qui formaient une couche rose par-dessus la peau, sont maintenant dans le système `peau`. La
  peau n'est pas gonflée au build : la décaler le long de ses normales déplacerait aussi sa surface
  interne et rétrécirait les orifices (paupières, narines, lèvres).
- **Vaisseaux absents de BodyParts3D** (`full_body`) : des segments manquent dans la source, ce qui
  interrompt l'arbre vasculaire : carotide commune → carotide interne (6 cm), subclavière → artère
  vertébrale (segments V1-V2, 5 cm), veine poplitée → veine tibiale postérieure (3,5 cm) ; la jugulaire
  interne ne mesure que 4 cm ; il n'y a ni carotide externe ni ses branches, ni jugulaires externe et
  antérieure, ni veines faciale et vertébrale. Les sinus de la dure-mère et la partie haute des jugulaires
  internes viennent de Z-Anatomy ; aucune source libre vérifiée n'a les **veines cérébrales** (grande veine
  cérébrale, veines cérébrales internes, basales, superficielles) : elles manquent toujours. Les grands
  vaisseaux aboutissent au cœur, rangé dans `organes`. Les jonctions présentes dans la source restent
  fermées : `check.py` mesure la distance entre les surfaces de 101 paires parent → branche, de l'aorte
  et des veines caves aux membres, et des sinus de la dure-mère aux jugulaires internes
  (`pipeline/anatomo_models/junctions.py`), et échoue au-delà de 1 mm.
- **Structures de Z-Anatomy** (`full_body`) : un autre dessin recalé sur nos os (2,1 mm RMS ; côtes 9 à 12 :
  3,3 à 4,2 mm). Les vaisseaux et nerfs sont des tubes ronds de rayon dessiné par Z-Anatomy : le sinus sagittal
  supérieur fait 4 mm de large au plus (section triangulaire en réalité). BodyParts3D n'ayant pas de sillons
  veineux ni de canaux nerveux, les sinus sigmoïdes et pétreux sont aux deux tiers dans l'os temporal, et les nerfs
  alvéolaires inférieurs et mentonniers dans la mandibule (où passe le canal mandibulaire). Le sinus droit et le
  sinus occipital sont mal placés dans Z-Anatomy (4,5 cm trop en avant) : le pipeline corrige ce décalage
  (`PARENT_FIX`). Ajouts synthétiques, droits : 7 mm entre sinus sigmoïde et veine jugulaire interne (bulbe
  jugulaire) et environ 2,5 cm entre les troncs sympathiques thoraciques de Z-Anatomy et lombaires de l'Open3DModel.
  Non repris : nerfs II, IV et ophtalmique (BodyParts3D les a déjà en entier), nerf facial, corde du tympan et nerf
  vestibulocochléaire (provenance non établie), rameau méningé du nerf maxillaire (dessiné hors du crâne), nerf vague
  sous la racine du cou (le gauche s'arrête en T2 et le droit porte les rameaux gastriques antérieurs, du côté
  gauche). Le sinus caverneux reste à 3 mm du sinus intercaverneux antérieur, comme dans Z-Anatomy.
- Les **noms français** (`data/fr_names.json`) couvrent toutes les structures. Ils
  ont été traduits puis relus par des agents, sans relecture humaine, et ne portent pas le côté
  (sauf quand il fait partie du nom). Conventions et points incertains :
  [`docs/NOMS.md`](docs/NOMS.md).
- Les **repères anatomiques** (osseux, attaches musculaires, pouls, repères cliniques ; voir
  [`docs/FORMAT.md`](docs/FORMAT.md#repères-anatomiques)) sont placés géométriquement, pas par un anatomiste.
- Dans `full_body`, le classement par système vient de l'arbre is-a FMA, avec les noms anglais
  en secours. Les erreurs relevées (cartilages et disques en `os`, segments du foie en `veines`, poils en
  `organes`…) sont corrigées par une table explicite, FMA ID par FMA ID, dans
  [`pipeline/anatomo_models/overrides.py`](pipeline/anatomo_models/overrides.py) ; ce que contient chaque
  système est décrit dans [`docs/FORMAT.md`](docs/FORMAT.md#systèmes). Le système `organes` reste
  hétérogène (viscères, encéphale, ligaments, cartilages).
