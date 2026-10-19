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
  Os du tarse : Talus, Calcanéus, Os naviculaire, Os cuboïde, Os cunéiforme médial / intermédiaire / latéral.
- Muscles de l'œil : « de l'œil » dans le nom (« Muscle oblique supérieur de l'œil »), le modèle ayant aussi
  des muscles obliques et droits de la tête.
- Séries segmentaires (rotateurs, interépineux, intertransversaires) : au pluriel, comme la TA.
- Le côté reste aussi dans le nom des veines pulmonaires et des veines intercostales supérieures (entrées
  distinctes de la TA ; terminaisons différentes à droite et à gauche).
- Lombaires : « processus costiforme » (et non « transverse ») pour les repères de L1 à L5.

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
| FMA86056 | myocardial zone 4 | posterior leaflet of mitral valve | Cuspide postérieure de la valve mitrale |
| FMA86064 | myocardial zone 12 | anterolateral head of lateral papillary muscle of left ventricle | Muscle papillaire antérieur du ventricule gauche |
| FMA85123, FMA85124 | fourth common palmar digital artery (on n'en décrit classiquement que trois) | medial proper palmar digital artery of little finger : le maillage longe le bord ulnaire du petit doigt jusqu'à la pulpe | Artère digitale palmaire propre médiale du petit doigt |
| FMA22954 | dorsal metacarpal vein | dorsal metatarsal veins : le maillage est sur les deux pieds, aucun morceau sur la main | Veines métatarsiennes dorsales |
| FMA8620 | right anterior segmental artery (poumon) | anterior segmental artery of kidney : le maillage est dans le rein droit, parmi les artères segmentaires rénales | Artère segmentaire antérieure du rein |
| FMA4771, FMA4785 | right / left superior epigastric vein | superficial epigastric vein : même maillage que FMA44340 / FMA44341, sous l'ombilic | Veine épigastrique superficielle |
| FMA49214 | wall of inflow part of left ventricle | posterior papillary muscle of left ventricle : même maillage que FMA7266 | Muscle papillaire postérieur du ventricule gauche |
| FMA71889, FMA76903 | caudate tributary of left hepatic bile duct / left duct of caudate lobe | un seul et même maillage | Conduit biliaire gauche du lobe caudé |
| FMA13884 | wall of ventricle | myocarde des deux ventricules | Paroi des ventricules (myocarde ventriculaire) |

Le format n'a pas de champ de synonymes : les anciens noms courants sont indiqués entre parenthèses
dans ce tableau seulement (muscle de la luette pour le muscle de l'uvule).

### Vaisseaux pulmonaires segmentaires (identifiants changés après la 1.4.1)

Jusqu'à la 1.4.1, quatre vaisseaux segmentaires du poumon portaient l'identifiant et le nom anglais du segment
bronchopulmonaire qu'ils irriguent ou drainent : BodyParts3D rattache leurs fichiers aux deux concepts, et le
segment l'emportait sur le vaisseau à égalité. Ils sont maintenant rattachés au concept du vaisseau
(`OWNER_FIXES` dans `pipeline/full_body.py`) ; les noms français ne changent pas.

| Ancien FMA ID (segment) | Nouveau FMA ID | Nom anglais | Nom français |
| --- | --- | --- | --- |
| FMA7376 | FMA8642 | left superior segmental artery | Artère segmentaire supérieure |
| FMA7377 | FMA8644 | left medial basal segmental artery | Artère segmentaire basale médiale |
| FMA7365 | FMA9422 | right medial basal segmental vein | Veine segmentaire basale médiale |
| FMA7386 | FMA9438 | left posterior segmental vein | Veine segmentaire postérieure |

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
| side of bony pelvis | Os coxal | Interprétation du nom FMA |
| cusps of aortic valve | Valvules antérieure (coronaire droite), postérieure gauche (coronaire gauche), postérieure droite (non coronaire) | Ancienne nomenclature anglaise, rapportée à la TA entre parenthèses |
| cusps of pulmonary valve | Valvules antérieure droite, antérieure gauche, postérieure | Positions de la source gardées ; correspondance avec la TA (antérieure, droite, gauche) non établie |
| splenial artery | Artère du splénium (artère péricalleuse postérieure) | Pas de forme française standard |
| intermediate tendon | Tendon intermédiaire du muscle digastrique | Déduit de la position du maillage (près de l'os hyoïde, sur la ligne médiane) |
| ureteric segment of renal artery | traduit littéralement | Probablement le rameau urétéral |
| celiac artery / celiac trunk, marginal artery (×2) | Tronc cœliaque, Artère marginale du côlon | Même maillage en double dans la source |
| posterior part of pelvis | Sacrum et coccyx | Le fichier source est rattaché au sacrum ; la hauteur du maillage (14 cm) et le repère « Apex du coccyx » laissent penser qu'il contient aussi le coccyx |
| intervertebral disk | Disque intervertébral T12-L1 | Concept générique ; T12-L1 d'après la position du maillage |
| set of calcaneal branches of posterior tibial artery (FMA71562) | Rameaux de l'artère circonflexe fémorale latérale | Le maillage n'est pas au talon mais à la racine de la cuisse, au contact de l'artère circonflexe fémorale latérale et en dehors d'elle ; identité exacte non établie. L'app ne le pose pas en quiz |
| hepatic segments VII et IX (FMA15745, FMA15747) | Segment hépatique VII, IX | Leurs maillages recouvrent ceux des segments VI et VIII ; l'app ne les pose pas en quiz |
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

### Les deux côtés dans `full_body`

Dans `full_body`, les nerfs Open3DModel du membre supérieur sont présents des deux côtés. Le nom français est le
même à droite et à gauche (pas de côté dans le nom). Le côté gauche prend le concept FMA gauche correspondant
(`LEFT`, `pipeline/anatomo_models/open3d_full_body.py`, vérifié dans la FMA de l'EBI : même libellé avec « left »).
Pour les concepts génériques sans côté (divisions du plexus brachial, nerfs digitaux), le nom anglais reçoit le
côté et le gauche prend l'identifiant `FMA…-L` : voir [`FORMAT.md`](FORMAT.md#le-manifeste).

## Nerfs du membre inférieur (Open3DModel, `full_body`)

Les 65 objets nerveux de l'export « lower limb » de l'Open3DModel sont rattachés à 62 concepts FMA par la table
`NERVES` de `pipeline/anatomo_models/open3d_lower.py`, avec la même méthode que pour le membre supérieur : FMA ID
et nom anglais vérifiés dans la FMA de l'EBI (OLS, octobre 2026), nom français dans la terminologie anatomique
internationale en français, sans côté. Comme ceux du membre supérieur, ces noms sont dans la table du pipeline et
pas dans `data/fr_names.json`. Ils sont présents des deux côtés de `full_body`, avec les mêmes règles que
ci-dessus. Aucun anatomiste ne les a relus.

| Objet Open3DModel | FMA | Nom français | Doute |
| --- | --- | --- | --- |
| `L1_root` … `S5_root` | FMA17673 … FMA18079 root of right first lumbar nerve … fifth sacral nerve | Racines du 1er nerf lombaire (L1) … du 5e nerf sacral (S5) | Les objets vont du cône médullaire aux foramens (queue de cheval) ; racines antérieure et postérieure non séparées |
| `Sympathic_trunk` | FMA6259 right sympathetic trunk | Tronc sympathique (parties lombaire et sacrale) | L'objet ne montre que les parties lombaire et sacrale |
| `Iliohypogastric_nerve, lateral cutaneous branch` + `…, anterior branch` | FMA16491 right iliohypogastric nerve | Nerf ilio-hypogastrique | La FMA n'a pas de concept pour ces rameaux cutanés (seulement les rameaux iliaque et hypogastrique) ; le premier objet contient aussi le tronc du nerf : fusionnés |
| `Genitofemoral_nerve, genital branch` | FMA20632 genital branch of right genitofemoral nerve | Rameau génital du nerf génito-fémoral | L'objet part du plexus lombaire : il contient aussi le tronc du nerf génito-fémoral |
| `Nerve_to_psoas_major_and_iliacus` | FMA20588 nerve to right psoas major | Nerf des muscles grand psoas et iliaque | Le concept FMA ne couvre que le grand psoas (l'iliaque est innervé par le nerf fémoral) |
| `Femoral_nerve, anterior cutaneous branches` | FMA45253 anterior cutaneous branch of right femoral nerve | Rameaux cutanés antérieurs du nerf fémoral | Concept FMA au singulier (le concept d'ensemble n'a pas de côté) |
| `Saphenous_branch_of_Femoralis_nerve` / `Saphenous_nerve (Medial crural cutaneous branches)` | FMA45263 right saphenous nerve / FMA75559 set of medial crural cutaneous branches of saphenous nerve | Nerf saphène / Rameaux cutanés cruraux médiaux du nerf saphène | Le premier objet est le nerf à la cuisse ; le second, à la jambe, contient aussi la fin du tronc du nerf |
| `Superior_clunial_nerve (posterior rami)` | FMA75468 set of superior clunial nerves | Nerfs cluniaux supérieurs | Rameaux postérieurs de L1–L3, reliés aux racines lombaires |
| `Nerve_to_obturator_internus (and superior gemellus)` | FMA78712 nerve to right obturator internus | Nerf du muscle obturateur interne | Il innerve aussi le jumeau supérieur |
| `Nerve_to_Levator_ani_and_coccygeus` | FMA82933 branch of sacral nerve plexus to right levator ani | Nerf des muscles élévateur de l'anus et coccygien | Le concept FMA ne couvre que l'élévateur de l'anus |
| `Lateral_dorsal_cutaneous_nerve` | FMA45367 right intermediate dorsal cutaneous nerve | Nerf cutané dorsal intermédiaire | Nommé « lateral » dans la source, mais il naît du nerf fibulaire superficiel avec le nerf cutané dorsal médial, et pas du nerf sural (qui a son propre objet, `Sural_nerve, Lateral_dorsal_cutaneous_nerve`) |
| `Lateral_calcaneal_nerves`, `Medial_calcaneal_branches_of_Tibial_nerve` | FMA45428, FMA45432 (concepts au singulier) | Rameaux calcanéens latéraux du nerf sural / médiaux du nerf tibial | Plusieurs rameaux, concept FMA au singulier |
| `Proper_plantar_digital_branches (Medial / Lateral plantar nerve)` | FMA75493 set of proper plantar digital nerves | Nerfs digitaux plantaires propres | Deux objets (nerfs plantaires médial et latéral) fusionnés : la FMA n'a pas de concept par nerf d'origine |
| `Dorsal_digital_branches_of_superficial / deep_fibular_nerve` | FMA75491 set of dorsal digital nerves of foot | Nerfs digitaux dorsaux du pied | Même chose pour les nerfs fibulaires superficiel et profond |

Non repris : le fragment de moelle spinale (`Spinal_cord_curve`, cône médullaire seul) et l'arachnoïde.

## Sinus et nerfs de Z-Anatomy (`full_body`)

Les 63 objets de Z-Anatomy en liste blanche sont rattachés à 61 identifiants par la table `OBJECTS` de
`pipeline/anatomo_models/zanatomy.py` : FMA ID et nom anglais vérifiés dans la FMA de l'EBI (OLS, octobre 2026),
nom français dans la terminologie anatomique internationale en français, sans côté. Comme ceux de l'Open3DModel,
ces noms sont dans la table du pipeline et pas dans `data/fr_names.json`. Z-Anatomy a les deux côtés : chaque côté
a son objet et le concept FMA de son côté. Quatre concepts existaient déjà dans le modèle et sont complétés (veines
jugulaires internes, troncs sympathiques : leur nom ne change pas, sauf le nom français du tronc sympathique, qui
devient « Tronc sympathique » au lieu de « Tronc sympathique (parties lombaire et sacrale) »). Aucun anatomiste ne
les a relus.

| Objet Z-Anatomy | FMA | Nom français | Doute |
| --- | --- | --- | --- |
| `Straight sinus` | FMA50769 straight sinus | Sinus droit | « droit » au sens de rectiligne, pas de côté |
| `Basilar venous plexus` | FMA50783 basilar venous plexus | Plexus basilaire | — |
| `Anterior/Posterior division of mandibular nerve` | FMA53062/FMA53064 anterior/posterior trunk of right mandibular nerve | Tronc antérieur/postérieur du nerf mandibulaire | Z-Anatomy dessine le nerf mandibulaire par ses deux troncs, sans tronc commun |
| `Nerve to mylohyoid muscle` | FMA53248 right mylohyoid nerve | Nerf mylohyoïdien | — |
| `Accessory nerve (XI)` | FMA50897 right spinal accessory nerve | Nerf accessoire | La FMA nomme « spinal accessory nerve » le nerf accessoire |
| `Trigeminal nerve (V)` | FMA50884 right trigeminal nerve | Nerf trijumeau | L'objet est la racine et le ganglion ; ses branches sont des structures à part |
| `Vagus nerve (X)` | FMA6219 right vagus nerve | Nerf vague | Partie cervicale seulement (jusqu'aux premières côtes) |
| `Intercostal nerves` | FMA75467 / FMA75467-L set of right/left intercostal nerves | Nerfs intercostaux | Ensemble sans côté dans la FMA : identifiant `-L` à gauche ; 11 nerfs par côté, sans nerf subcostal |
| `Sympathetic nerves` | FMA75599 / FMA75599-L set of communicating branches of right/left sympathetic trunk with spinal nerves | Rameaux communicants | Nommés « Sympathetic nerves » dans la source ; ce sont les rameaux qui relient le tronc aux nerfs intercostaux (blancs et gris confondus) |
| `Sympathetic trunk` + `Ganglia of sympathetic trunk` | FMA6259 right sympathetic trunk (avec l'Open3DModel) | Tronc sympathique | Parties cervicale et thoracique, ajoutées aux parties lombaire et sacrale de l'Open3DModel |

Sinus de la dure-mère (sagittaux, transverses, sigmoïdes, pétreux, caverneux, intercaverneux, occipital), veines
ophtalmiques et nerfs olfactif, oculomoteur, abducens, glossopharyngien, hypoglosse, maxillaire, buccal, lingual,
alvéolaire inférieur et mentonnier : concept FMA du même nom, sans doute particulier.
