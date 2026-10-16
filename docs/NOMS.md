# Noms français des structures

`data/fr_names.json` associe à chaque FMA ID le nom français affiché dans l'app. Il couvre toutes
les structures des modèles, sauf la peau (`integumentary system`). Les noms ont été traduits depuis
les noms anglais de BodyParts3D, puis relus par des agents indépendants. Aucun anatomiste ne les a
relus.

## Conventions

- Nomenclature anatomique internationale en français, celle des cours actuels : Ulna, Fibula,
  Patella, gastro-omentale, adducteur minimal. Deux exceptions à la TA, plus courantes en cours :
  « lombaire » (et non « lombale ») et « cristallin ».
- Majuscule initiale seulement ; « Muscle », « Artère », « Veine », « Nerf » en toutes lettres.
  « branch » donne « Rameau ». Font exception les branches droite et gauche de la veine porte, et
  les branches antérieure et postérieure de l'artère rénale (ses deux divisions).
- Les chefs et les parties suivent le nom du muscle : « Muscle deltoïde, partie acromiale ».
- **Pas de côté du corps dans le nom** : la paire droite/gauche partage le même nom, et l'app
  affiche le côté à part. Il est lu dans le nom anglais, voir `sideOf` dans l'app.
- Le côté reste dans le nom quand il désigne une autre structure : artère coronaire droite,
  ventricule gauche, artères et veines gastriques, gastro-omentales et coliques, veines et
  conduits hépatiques, artères pulmonaires et lobaires, bronches principales, veine marginale
  gauche, valvules semi-lunaires.
- « droit » peut aussi traduire rectus : muscle droit fémoral, muscle cricothyroïdien partie droite.
  Ce n'est pas un côté.
- « set of X » se traduit au pluriel.

## Points incertains

Les noms sources qui semblent erronés sont traduits tels quels.

| Nom anglais | Nom français | Doute |
| --- | --- | --- |
| faucial part of mouth | Isthme du gosier | Nom FMA peu courant, classé en muscles |
| fourth common palmar digital artery | 4e artère digitale palmaire commune | On en décrit classiquement trois |
| side of bony pelvis | Os coxal | Interprétation du nom FMA |
| upper jaw / lower jaw | Mâchoire supérieure / inférieure | Classés en organes, distincts de maxilla et mandible |
| cusps of aortic valve | Valvules antérieure (coronaire droite), postérieure gauche (coronaire gauche), postérieure droite (non coronaire) | Ancienne nomenclature anglaise, rapportée à la TA entre parenthèses |
| cusps of pulmonary valve | Valvules antérieure droite, antérieure gauche, postérieure | Positions de la source gardées ; correspondance avec la TA (antérieure, droite, gauche) non établie |
| splenial artery | Artère du splénium (artère péricalleuse postérieure) | Pas de forme française standard |
| intermediate tendon | Tendon intermédiaire du muscle digastrique | Déduit de la position du maillage (près de l'os hyoïde, sur la ligne médiane) |
| segments bronchopulmonaires classés en artères ou en veines | (traduits comme segments) | Classement de la source |
| ureteric segment of renal artery | traduit littéralement | Probablement le rameau urétéral |
| cheek | Joue | Classé en os ; la boîte correspond à l'os zygomatique |
| skeleton of mouth | Squelette de la bouche | Nom FMA peu courant |
| occipital part of head | Partie occipitale de la tête | Classé en os ; sans doute l'os occipital |
| celiac artery / celiac trunk, marginal artery (×2) | Tronc cœliaque, Artère marginale du côlon | Même maillage en double dans la source |
