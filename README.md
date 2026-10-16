# anatomo-models

Modèles 3D anatomiques de l'app Anatomo, et le pipeline qui les produit à partir de
[BodyParts3D](https://dbarchive.biosciencedbc.jp/en/bodyparts3d/) et, pour les nerfs du membre
supérieur, de l'[Open3DModel](https://anatomytool.org/node/63906) (AnatomyTOOL).

Les modèles sont des œuvres dérivées publiées en libre accès : `full_body` sous **CC BY-SA 2.1 Japon**,
la licence de BodyParts3D ; `upper_limb`, qui contient aussi les nerfs de l'Open3DModel (CC BY-SA 4.0),
sous **CC BY-SA 4.0**. Le code du pipeline est sous licence MIT.
Voir [`LICENSE`](LICENSE) et [`CREDITS.md`](CREDITS.md).

## Télécharger les modèles

Les fichiers `.glb` ne sont pas versionnés dans git : ils sont attachés aux
[Releases](https://github.com/AnatomoOrg/anatomo-models/releases) (`v<VERSION>`), avec leurs
manifestes, leurs repères anatomiques, une somme SHA-256 et les textes de licence.

| Modèle | Contenu | Maillages (draw calls) |
|---|---|---|
| `upper_limb` | Membre supérieur droit et ceinture scapulaire (MVP) : os, muscles, artères, veines, nerfs | 5 |
| `full_body` | Corps entier, tous systèmes (contexte) | 7 |

Chaque modèle a **un maillage par système** au lieu d'un maillage par structure (le prototype
en avait 2 234 pour le corps entier), et garde la sélection structure par structure grâce à un
indice de structure par sommet. Le format est décrit dans [`docs/FORMAT.md`](docs/FORMAT.md).

## Construire

```sh
pip install -r pipeline/requirements.txt
pipeline/fetch_bp3d.sh bp3d                 # ~750 Mo, sommes SHA-256 vérifiées
pipeline/fetch_open3d.sh bp3d/open3d        # nerfs du membre supérieur, OBJ ~21 Mo, géométrie seule
python pipeline/build.py bp3d build         # ou --only upper_limb / --only full_body
python pipeline/check.py build/upper_limb.json build/full_body.json
python -m pytest -q tests
```

## Publier une version

Changer `VERSION` sur `main`. Le workflow `Release models` reconstruit les modèles depuis les
sources, les vérifie (cohérence glb ↔ manifeste, validateur glTF Khronos) et crée la release
`v<VERSION>`. Une release existante n'est jamais écrasée.

### Si le fichier Open3DModel change en amont

`upper-limb-obj.zip` est épinglé par sa somme SHA-256 (`pipeline/open3d.sha256`) ; AnatomyTOOL le met
parfois à jour (dernière version datée du 14/10/2026). Si `fetch_open3d.sh` signale une somme
différente, le build s'arrête : rien n'est publié avec un fichier non relu. Pour adopter la nouvelle
version :

1. Relire la licence et le crédit demandés sur <https://anatomytool.org/node/63906> et
   <https://anatomytool.org/node/63903> (toujours CC BY-SA 4.0, export OBJ sans texture) ; reporter un
   changement de crédit dans `pipeline/anatomo_models/open3d.py` (`CREDIT`) et `CREDITS.md`.
2. Télécharger le zip, vérifier qu'il ne contient que des `.obj` (`unzip -l`), calculer sa somme
   (`sha256sum`) et la mettre dans `pipeline/open3d.sha256`.
3. `pipeline/fetch_open3d.sh bp3d/open3d && python pipeline/build.py bp3d build --only upper_limb` :
   le build échoue si un objet de `NERVES` ou un os de `BONES` a disparu ou a été renommé (adapter la
   table), ou si le recalage dépasse 4 mm RMS. Contrôler le journal du recalage et le nombre de nerfs.
4. `python pipeline/check.py …`, `python -m pytest -q tests`, puis mettre à jour la date du fichier
   dans `CREDITS.md`.

Aucune copie binaire n'est gardée dans git ; une release déjà publiée contient les modèles construits.

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
- Fusion des sommets dupliqués avant décimation (sinon la décimation ouvre des trous), puis
  décimation : 20 % pour le membre supérieur (minimum 3 000 triangles par structure, environ
  470 000 au total hors nerfs), environ 1,5 M triangles pour le corps entier.
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

- BodyParts3D n'a **pas de nerfs du membre supérieur** : ceux de `upper_limb` viennent de
  l'Open3DModel, un autre sujet recalé sur nos os. Après recalage, quelques nerfs touchent encore
  un os de quelques millimètres (nerf radial dans le sillon du nerf radial, jusqu'à 5,6 mm ; nerf
  cutané latéral inférieur du bras, nerf suprascapulaire, jusqu'à 3,3 mm). Les nerfs digitaux suivent
  la position des doigts de l'Open3DModel, proche de la nôtre. Le nerf thoracodorsal et le nerf
  intercostobrachial manquent (absents de la source). Points anatomiques incertains : voir
  [`docs/NOMS.md`](docs/NOMS.md#nerfs-du-membre-supérieur-open3dmodel).
- Le grand dorsal et le chef profond du court fléchisseur du pouce (dont le fichier 4.0 est du mauvais
  côté) viennent de la 3.0 seule, recalés par le champ de déplacement : leur position est moins sûre
  que celle des autres structures du membre supérieur.
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
- Les **noms français** (`data/fr_names.json`) couvrent toutes les structures sauf la peau. Ils
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
