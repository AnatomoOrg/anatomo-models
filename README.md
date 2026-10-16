# anatomo-models

Modèles 3D anatomiques de l'app Anatomo, et le pipeline qui les produit à partir de
[BodyParts3D](https://dbarchive.biosciencedbc.jp/en/bodyparts3d/).

Les modèles sont des œuvres dérivées de BodyParts3D, publiées en libre accès sous
**CC BY-SA 2.1 Japon**, la licence de la source. Le code du pipeline est sous licence MIT.
Voir [`LICENSE`](LICENSE) et [`CREDITS.md`](CREDITS.md).

## Télécharger les modèles

Les fichiers `.glb` ne sont pas versionnés dans git : ils sont attachés aux
[Releases](https://github.com/AnatomoOrg/anatomo-models/releases) (`v<VERSION>`), avec leurs
manifestes, une somme SHA-256 et les textes de licence.

| Modèle | Contenu | Maillages (draw calls) |
|---|---|---|
| `upper_limb` | Membre supérieur droit (MVP) : os, muscles, artères, veines | 4 |
| `full_body` | Corps entier, tous systèmes (contexte) | 7 |

Chaque modèle a **un maillage par système** au lieu d'un maillage par structure (le prototype
en avait 2 234 pour le corps entier), et garde la sélection structure par structure grâce à un
indice de structure par sommet. Le format est décrit dans [`docs/FORMAT.md`](docs/FORMAT.md).

## Construire

```sh
pip install -r pipeline/requirements.txt
pipeline/fetch_bp3d.sh bp3d                 # ~750 Mo, sommes SHA-256 vérifiées
python pipeline/build.py bp3d build         # ou --only upper_limb / --only full_body
python pipeline/check.py build/upper_limb.json build/full_body.json
python -m pytest -q tests
```

## Publier une version

Changer `VERSION` sur `main`. Le workflow `Release models` reconstruit les modèles depuis les
sources, les vérifie (cohérence glb ↔ manifeste, validateur glTF Khronos) et crée la release
`v<VERSION>`. Une release existante n'est jamais écrasée.

## Sources et choix du pipeline

- **Os et muscles du membre supérieur** : BodyParts3D 3.0, maillages « 95 % » (environ cinq fois
  plus denses que la 4.0), recalés dans le repère de la 4.0 par une translation constante
  (0,7 ; −3,7 ; −10,3 mm). La clavicule et la scapula diffèrent de quelques millimètres.
- **Vaisseaux et corps entier** : BodyParts3D 4.0, maillages « 99 % ».
- Fusion des sommets dupliqués avant décimation (sinon la décimation ouvre des trous), puis
  décimation : 20 % pour le membre supérieur (minimum 3 000 triangles par structure, environ
  470 000 au total), environ 1,5 M triangles pour le corps entier.
- Chaque fichier élément de BodyParts3D est rattaché à son concept FMA le plus spécifique (dans
  les arbres is-a et part-of).
- Le build échoue si les maillages 3.0 manquent (pas de repli silencieux sur la 4.0) ; un concept
  dont une partie des fichiers est prise par un concept plus précis reste en 4.0, pour ne pas
  dessiner deux fois la même géométrie.
- BodyParts3D 4.0 inverse droite et gauche pour le court fléchisseur du pouce et le constricteur
  moyen du pharynx : le pipeline
  échange les deux maillages quand une paire droite/gauche est entièrement du mauvais côté.

## Limites connues

- BodyParts3D n'a **pas de nerfs du membre supérieur** ; le grand dorsal et le trapèze manquent
  aussi. Z-Anatomy (CC BY-SA 4.0) les a, mais son dépôt n'est pas accessible depuis notre
  environnement de build pour l'instant.
- Les **noms français** (`data/fr_names.json`) ne couvrent que le membre supérieur et restent à
  relire ; les autres structures ont `fr: null`.
- Les **repères osseux** de l'humérus sont placés géométriquement, pas par un anatomiste.
- Dans `full_body`, le classement par système vient de l'arbre is-a FMA, avec les noms anglais
  en secours : quelques structures peuvent être mal rangées (notamment dans `organes`).
