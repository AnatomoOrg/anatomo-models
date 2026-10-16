# Noms français des structures

`data/fr_names.json` associe à chaque FMA ID le nom français affiché dans l'app. Il couvre toutes
les structures des modèles, y compris la peau (`integumentary system`, « Peau »). Les noms ont été traduits depuis
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

- Disques intervertébraux : nommés par les deux vertèbres qu'ils unissent (« Disque intervertébral C2-C3 »).
  Le nom FMA porte la vertèbre au-dessus du disque (« intervertebral disk of axis » = C2-C3), ce que confirme
  la position des maillages.
- Repères osseux : le nom porte l'os quand le même nom existe sur un autre os ou qu'il est ambigu hors
  contexte (« Condyle latéral du tibia (plateau tibial) », « Épicondyle médial de l'humérus », « Processus
  coronoïde de l'ulna »). Les attaches musculaires gardent un nom court : le muscle donne le contexte.
- Humérus : « tubercule majeur » et « tubercule mineur » (terminologie internationale, celle des fiches de
  l'app), et non « grand » et « petit tubercule ». « Grand trochanter » et « petit trochanter » restent
  d'usage courant et sont gardés.
- Os du carpe : Scaphoïde, Lunatum, Triquétrum, Pisiforme, Trapèze (os), Trapézoïde, Capitatum, Hamatum.

## Maillages rattachés à un concept plus large

Le pipeline rattache chaque fichier de BodyParts3D au concept FMA qui le possède le plus précisément. Pour
quelques structures, ce choix tombe sur un concept englobant (une région, une paroi) alors que le seul
maillage est celui d'une structure précise. Le FMA ID et le nom anglais du manifeste restent ceux du concept
retenu, pour ne pas changer les identifiants ; **le nom français décrit ce que montre le maillage**.

| FMA ID | Nom anglais (concept retenu) | Maillage | Nom français |
| --- | --- | --- | --- |
| FMA53637, FMA53638 | right / left cheek | right / left zygomatic bone | Os zygomatique |
| FMA61670 | skeleton of mouth | mandible | Mandibule |
| FMA49187 | occipital part of head | occipital bone | Os occipital |
| FMA52801 | basicranium | ethmoid | Os ethmoïde |
| FMA24228 | posterior part of pelvis | sacrum | Sacrum et coccyx |
| FMA59665 | septum of internal nose | vomer | Vomer |
| FMA59671, FMA59672 | lateral wall of internal nose | inferior nasal concha | Cornet nasal inférieur |
| FMA59838 | cartilaginous part of nasal septum | septal nasal cartilage | Cartilage du septum nasal |
| FMA54397, FMA54398 | upper jaw / lower jaw | gingiva of upper / lower jaw | Gencive supérieure / inférieure |
| FMA59992 | faucial part of mouth | uvular muscle | Muscle de l'uvule (ancien nom : muscle de la luette) |
| FMA50071 | right lateral superficial chest wall | right serratus anterior | Muscle dentelé antérieur |
| FMA58406 | investing fascia of left free upper limb | flexor retinaculum of left wrist | Rétinaculum des fléchisseurs du poignet |
| FMA58100, FMA58107 | wall of left eyeball, vascular layer of right eyeball | choroid | Choroïde |
| FMA62003 | metencephalon | cerebellum | Cervelet |
| FMA75007 | cavity of neuraxis | central canal of spinal cord | Canal central de la moelle spinale |
| FMA259248 | content of abdomen | abdominal aorta | Aorte abdominale |
| FMA68317, FMA68318 | superior / inferior division of upper lobe part of left bronchial tree | left anterior segmental / superior lingular bronchial tree | Arbre bronchique segmentaire antérieur / lingulaire supérieur |
| FMA7376, FMA7377 | left superior / medial basal bronchopulmonary segment | left superior / medial basal segmental artery | Artère segmentaire supérieure / basale médiale |
| FMA7365, FMA7386 | right medial basal / left posterior bronchopulmonary segment | segmental veins | Veine segmentaire basale médiale / postérieure |
| FMA86056 | myocardial zone 4 | posterior leaflet of mitral valve | Cuspide postérieure de la valve mitrale |
| FMA86064 | myocardial zone 12 | anterolateral head of lateral papillary muscle of left ventricle | Muscle papillaire antérieur du ventricule gauche |

Le format n'a pas de champ de synonymes : les anciens noms courants sont indiqués entre parenthèses
dans ce tableau seulement (muscle de la luette pour le muscle de l'uvule).

### Identifiants à connaître

- **FMA58406** : le rétinaculum des fléchisseurs du poignet gauche (`full_body`) garde l'identifiant et
  le nom anglais du concept qui possède le fichier source, `investing fascia of left free upper limb`,
  alors que le maillage est le rétinaculum. L'ID et le nom anglais restent stables d'une version à
  l'autre ; seul le nom français décrit le maillage. Son homologue droit est `FMA40120` (`flexor
  retinaculum of right wrist`) ; le concept gauche propre de la FMA (`FMA40121`) n'est pas utilisé.
- **Dentelé antérieur droit** : `FMA50071` (`right lateral superficial chest wall`, maillage 4.0) dans
  `full_body`, `FMA13398` (`right serratus anterior`, maillage 3.0) dans `upper_limb`. Une app qui relie
  les deux modèles ne peut donc pas se fier au seul FMA ID pour cette structure ; le gauche est
  `FMA13399` dans `full_body`.

## Points incertains

Les noms sources qui semblent erronés sont traduits tels quels.

| Nom anglais | Nom français | Doute |
| --- | --- | --- |
| fourth common palmar digital artery | 4e artère digitale palmaire commune | On en décrit classiquement trois |
| side of bony pelvis | Os coxal | Interprétation du nom FMA |
| cusps of aortic valve | Valvules antérieure (coronaire droite), postérieure gauche (coronaire gauche), postérieure droite (non coronaire) | Ancienne nomenclature anglaise, rapportée à la TA entre parenthèses |
| cusps of pulmonary valve | Valvules antérieure droite, antérieure gauche, postérieure | Positions de la source gardées ; correspondance avec la TA (antérieure, droite, gauche) non établie |
| splenial artery | Artère du splénium (artère péricalleuse postérieure) | Pas de forme française standard |
| intermediate tendon | Tendon intermédiaire du muscle digastrique | Déduit de la position du maillage (près de l'os hyoïde, sur la ligne médiane) |
| ureteric segment of renal artery | traduit littéralement | Probablement le rameau urétéral |
| celiac artery / celiac trunk, marginal artery (×2) | Tronc cœliaque, Artère marginale du côlon | Même maillage en double dans la source |
| posterior part of pelvis | Sacrum et coccyx | Le fichier source est rattaché au sacrum ; la hauteur du maillage (14 cm) et le repère « Apex du coccyx » laissent penser qu'il contient aussi le coccyx |
| intervertebral disk | Disque intervertébral T12-L1 | Concept générique ; T12-L1 d'après la position du maillage |
| myocardial zone 12 | Muscle papillaire antérieur du ventricule gauche | Le muscle papillaire « latéral » de la FMA correspond au muscle papillaire antérieur de la TA |

## Nerfs du membre supérieur (Open3DModel)

Les 50 objets nerveux de l'Open3DModel n'ont pas de nom FMA : la table `NERVES` de
`pipeline/anatomo_models/open3d.py` associe chacun à un FMA ID, au nom FMA anglais et à un nom
français (terminologie anatomique internationale en français). Ces noms ne sont pas dans
`data/fr_names.json` (réservé aux structures BodyParts3D). Les FMA ID et les noms anglais ont été
vérifiés dans la FMA publiée par l'EBI (OLS, octobre 2026) ; les choix n'ont pas été relus par un
anatomiste. Quand la FMA a un concept du côté droit, il est utilisé ; sinon (objets qui regroupent
plusieurs nerfs), le concept d'ensemble ou générique, sans côté.

| Objet Open3DModel | FMA | Nom français | Doute |
| --- | --- | --- | --- |
| `T1_root.r` | FMA6073 right first intercostal nerve | Rameau antérieur du 1er nerf thoracique (racine T1 du plexus brachial) | La FMA nomme ce rameau « first intercostal nerve » (synonyme : anterior ramus of first thoracic nerve) ; l'objet n'en montre que la racine du plexus |
| `Anterior_divisions…`, `Posterior_divisions…` | FMA77549, FMA77550 (set of …) | Divisions antérieures / postérieures du plexus brachial | Un seul objet pour les trois divisions : concept d'ensemble, sans côté |
| `Radial_nerve_(deep_branch)` + `…(posterior_interosseus_n)` | FMA65335 right posterior interosseous nerve | Rameau profond du nerf radial et nerf interosseux postérieur | Deux objets fusionnés : la FMA fait du rameau profond un synonyme du nerf interosseux postérieur |
| `Ulnar_nerve_Superficial_br_Common_palmar_digital_n` + `Ulnar_nerve_Communicating_br` | FMA44894 superficial branch of right ulnar nerve | Rameau superficiel du nerf ulnaire | L'objet part de la division du nerf ulnaire (rameau superficiel et son nerf digital palmaire commun). Le rameau communicant avec le nerf médian n'a dans la FMA qu'un concept de variante (`FMA0326786`, identifiant atypique) : il est fusionné ici |
| `Median_nerve_Common_palmar_digital_nerve_of_the_thumb` | FMA44851 first common palmar digital branch of right median nerve | 1er nerf digital palmaire commun du nerf médian | La FMA fait naître de ce nerf les deux nerfs digitaux palmaires propres du pouce ; la numérotation varie selon les auteurs |
| `Median_nerve_Common_palmar_digital_nerves` | FMA44840 (générique) | Nerfs digitaux palmaires communs du nerf médian | Les autres nerfs communs, regroupés |
| `Median_nerve_Proper_palmar_digital_nerves` | FMA44853 (générique) | Nerfs digitaux palmaires propres du nerf médian | Concept parent de celui du pouce (FMA44854), utilisé à part pour l'objet du pouce |
| `Median_nerve_Recurrent_br` | FMA291310 thenar muscular branch of right median nerve | Rameau thénarien du nerf médian (rameau récurrent) | |
| `Axillary_nerve_-_superior_lateral_br_cutaneous_nerve` | FMA37073 right axillary nerve | Nerf axillaire | L'objet contient aussi le nerf cutané latéral supérieur du bras (FMA81294), non séparé |
| `Subclavian_nerve` | FMA65285 right subclavian nerve | Nerf subclavier | Aussi appelé nerf du muscle subclavier |
| `Ulnar_nerve_Palmar_cutaneous_br` | FMA65349 palmar branch of right ulnar nerve | Rameau palmaire du nerf ulnaire | Rameau cutané palmaire |

Absents de la source : nerf thoracodorsal, nerf intercostobrachial, nerf interosseux antérieur,
pas d'objet séparé pour les rameaux musculaires.
