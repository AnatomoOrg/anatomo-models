"""Lower-limb nerves from the Open3DModel (AnatomyTOOL; Leiden, Radboud...), geometry only.

Source: the "lower limb" OBJ export of the Open3DModel project, CC BY-SA 4.0
(https://anatomytool.org/node/63936), fetched by pipeline/fetch_open3d.sh and pinned by SHA-256
(pipeline/open3d.sha256). Like the upper-limb export, the OBJ has no colours, materials or textures; the
textures of the Blender and glb exports are CC BY-NC-SA and are never downloaded nor used.

Same frame as the upper-limb OBJ (metres, +Y up, +Z anterior, subject's left at +X), right side only
(the vertebrae, sacrum and coccyx are whole). Its nerves go into the whole-body model on both sides, see
open3d_full_body.py; `BONES` are the registration targets of the right side.

`NERVES` maps each nerve object to an FMA concept (checked against the FMA, EBI OLS, October 2026), its FMA
English name and a French name. Objects that share a concept are merged into one structure. Left out: the
spinal cord stump ("Spinal_cord_curve_Spinal_cord", conus medullaris only) and the arachnoid mater.
"""
OBJ = "lower-limb.obj"
SOURCE = {"name": "Open3DModel, lower limb (AnatomyTOOL), geometry only",
          "url": "https://anatomytool.org/node/63936", "license": "CC-BY-SA-4.0"}
# Credit line requested by AnatomyTOOL for the lower-limb model (https://anatomytool.org/node/63936).
CREDIT = ('"Open3DModel - Lower limb - English labels" at AnatomyTOOL.org by Open3D project, Jan Kooloos, '
          'RadboudUMC, Eungyeol Lee, LUMC et al, license: Creative Commons Attribution-ShareAlike')

# Open3D bone object -> FMA id of the same right-sided (or median) bone in the whole-body model. The lumbar
# vertebrae and the sacrum hold the roots and plexuses, the tarsal and metatarsal bones the foot (phalanges
# are left out: toe pose). BodyParts3D draws the sacrum and the coccyx as one mesh (FMA24228, "posterior
# part of pelvis"), and the right hip bone as "right side of bony pelvis" (FMA20226).
BONES = {"Lumbar_vertebra_(L1)": "FMA13072", "Lumbar_vertebra_(L2)": "FMA13073",
         "Lumbar_vertebra_(L3)": "FMA13074", "Lumbar_vertebra_(L4)": "FMA13075",
         "Lumbar_vertebra_(L5)": "FMA13076", "Sacrum": "FMA24228", "Coccyx": "FMA24228",
         "Hip_bone.r": "FMA20226", "Femur.r": "FMA24474", "Patella.r": "FMA24486", "Tibia.r": "FMA24477",
         "Fibula.r": "FMA24480", "Talus.r": "FMA24482", "Calcaneus.r": "FMA24497",
         "Navicular_bone.r": "FMA24500", "Cuboid_bone.r": "FMA24528", "Medial_cuneiform_bone.r": "FMA24521",
         "Intermediate_cuneiform_bone.r": "FMA24523", "Lateral_cuneiform_bone.r": "FMA24525",
         "First_metatarsal_bone.r": "FMA24507", "Second_metatarsal_bone.r": "FMA24509",
         "Third_metatarsal_bone.r": "FMA24511", "Fourth_metatarsal_bone.r": "FMA24513",
         "Fifth_metatarsal_bone.r": "FMA24515"}
# The same bones on the left side (median bones are their own counterpart).
LEFT_BONES = {"FMA20226": "FMA20227", "FMA24474": "FMA24475", "FMA24486": "FMA24487", "FMA24477": "FMA24478",
              "FMA24480": "FMA24481", "FMA24482": "FMA24483", "FMA24497": "FMA24498", "FMA24500": "FMA24501",
              "FMA24528": "FMA24529", "FMA24521": "FMA24522", "FMA24523": "FMA24524", "FMA24525": "FMA24526",
              "FMA24507": "FMA24508", "FMA24509": "FMA24510", "FMA24511": "FMA24512", "FMA24513": "FMA24514",
              "FMA24515": "FMA24516"}

# A right-sided concept is used when the FMA has one; objects that group several nerves map to the FMA set.
# Open3D object -> (FMA id, FMA English name, French name)
NERVES = {
    # Roots of the spinal nerves: the objects run from the conus medullaris through the cauda equina to the
    # intervertebral or sacral foramina, where the plexus objects begin.
    "L1_root.r": ("FMA17673", "root of right first lumbar nerve", "Racines du 1er nerf lombaire (L1)"),
    "L2_root.r": ("FMA17675", "root of right second lumbar nerve", "Racines du 2e nerf lombaire (L2)"),
    "L3_root.r": ("FMA17678", "root of right third lumbar nerve", "Racines du 3e nerf lombaire (L3)"),
    "L4_root.r": ("FMA17680", "root of right fourth lumbar nerve", "Racines du 4e nerf lombaire (L4)"),
    "L5_root.r": ("FMA17682", "root of right fifth lumbar nerve", "Racines du 5e nerf lombaire (L5)"),
    "S1_root.r": ("FMA18068", "root of right first sacral nerve", "Racines du 1er nerf sacral (S1)"),
    "S2_root.r": ("FMA18070", "root of right second sacral nerve", "Racines du 2e nerf sacral (S2)"),
    "S3_root.r": ("FMA18072", "root of right third sacral nerve", "Racines du 3e nerf sacral (S3)"),
    "S4_root.r": ("FMA18075", "root of right fourth sacral nerve", "Racines du 4e nerf sacral (S4)"),
    "S5_root.r": ("FMA18079", "root of right fifth sacral nerve", "Racines du 5e nerf sacral (S5)"),
    "Coccygeal_nerve.r": ("FMA6438", "right coccygeal nerve", "Nerf coccygien"),
    # The object runs along the lumbar vertebrae and the sacrum only.
    "Sympathic_trunk.r": ("FMA6259", "right sympathetic trunk", "Tronc sympathique (parties lombaire et sacrale)"),
    # Plexuses
    "Lumbar_plexus.r": ("FMA20674", "right lumbar nerve plexus", "Plexus lombaire"),
    "Lumbosacral_Trunk.r": ("FMA65536", "right lumbosacral trunk", "Tronc lombo-sacral"),
    "Sacral_plexus.r": ("FMA63660", "right sacral nerve plexus", "Plexus sacral"),
    # Lumbar plexus. The FMA has no concept for the lateral and anterior cutaneous branches of the
    # iliohypogastric nerve: the first object also holds the trunk of the nerve, both are merged.
    "Iliohypogastric_nerve,_lateral_cutaneous_branch.r_": ("FMA16491", "right iliohypogastric nerve",
                                                           "Nerf ilio-hypogastrique"),
    "Iliohypogastric_nerve,_anterior_branch.r": ("FMA16491", "right iliohypogastric nerve", "Nerf ilio-hypogastrique"),
    "Ilioinguinal_nerve.r": ("FMA16493", "right ilioinguinal nerve", "Nerf ilio-inguinal"),
    # The genital branch object starts at the lumbar plexus: it holds the trunk of the genitofemoral nerve.
    "Genitofemoral_nerve,_genital_branch.r_": ("FMA20632", "genital branch of right genitofemoral nerve",
                                               "Rameau génital du nerf génito-fémoral"),
    "Genitofemoral_nerve,_femoral_branch.r_": ("FMA20634", "femoral branch of right genitofemoral nerve",
                                               "Rameau fémoral du nerf génito-fémoral"),
    "Lateral_femoral_cuteneous_nerve.r": ("FMA16497", "right lateral femoral cutaneous nerve",
                                          "Nerf cutané latéral de la cuisse"),
    # FMA: nerve to psoas major only (the iliacus is supplied by the femoral nerve).
    "Nerve_to_psoas_major_and_iliacus.r": ("FMA20588", "nerve to right psoas major",
                                           "Nerf des muscles grand psoas et iliaque"),
    "Femoral_nerve.r": ("FMA16499", "right femoral nerve", "Nerf fémoral"),
    "Femoral_nerve,_muscular_branches.r": ("FMA75506", "set of muscular branches of femoral nerve",
                                           "Rameaux musculaires du nerf fémoral"),
    "Femoral_nerve,_anterior_cutaneous_branches.r_": ("FMA45253", "anterior cutaneous branch of right femoral nerve",
                                                      "Rameaux cutanés antérieurs du nerf fémoral"),
    "Saphenous_branch_of_Femoralis_nerve.r": ("FMA45263", "right saphenous nerve", "Nerf saphène"),
    "Infrapatellar_branch_of_Saphenous_nerve.r": ("FMA45326", "infrapatellar branch of right saphenous nerve",
                                                  "Rameau infrapatellaire du nerf saphène"),
    "Saphenous_nerve_(Medial_crural_cutaneous_branches).r": (
        "FMA75559", "set of medial crural cutaneous branches of saphenous nerve",
        "Rameaux cutanés cruraux médiaux du nerf saphène"),
    "Obturator_nerve.r": ("FMA16501", "right obturator nerve", "Nerf obturateur"),
    "Obturator_nerve,_anterior_branch.r": ("FMA45308", "anterior branch of right obturator nerve",
                                           "Rameau antérieur du nerf obturateur"),
    "Obturator_nerve,_posterior_branch.r": ("FMA45310", "posterior branch of right obturator nerve",
                                            "Rameau postérieur du nerf obturateur"),
    "Obturator_nerve,_anterior_br,_cutaneous_br.r": ("FMA45313", "cutaneous branch of anterior branch of right "
                                                     "obturator nerve", "Rameau cutané du nerf obturateur"),
    # Posterior rami of L1-L3: the object joins the lumbar roots.
    "Superior_clunial_nerve_(posterior_rami).r": ("FMA75468", "set of superior clunial nerves",
                                                  "Nerfs cluniaux supérieurs"),
    # Sacral plexus
    "Superior_gluteal_nerve.r": ("FMA45344", "right superior gluteal nerve", "Nerf glutéal supérieur"),
    "Inferior_gluteal_nerve.r": ("FMA45346", "right inferior gluteal nerve", "Nerf glutéal inférieur"),
    "Nerve_to_quadratus_femoris.r": ("FMA78706", "nerve to right quadratus femoris", "Nerf du muscle carré fémoral"),
    "Nerve_to_obturator_internus_(and_superior_gemellus).r": ("FMA78712", "nerve to right obturator internus",
                                                              "Nerf du muscle obturateur interne"),
    # FMA: branch to levator ani only (the object also supplies the coccygeus).
    "Nerve_to_Levator_ani_and_coccygeus.r": ("FMA82933", "branch of sacral nerve plexus to right levator ani",
                                             "Nerf des muscles élévateur de l'anus et coccygien"),
    "Pudendal_nerve.r": ("FMA21863", "right pudendal nerve", "Nerf pudendal"),
    "Posterior_cutaneous_nerve_of_the_thigh.r": ("FMA45338", "right posterior femoral cutaneous nerve",
                                                 "Nerf cutané postérieur de la cuisse"),
    "Inferior_clunial_br._of_Post._cutaneous_nerve_of_the_thigh.": ("FMA75470", "set of inferior clunial nerves",
                                                                    "Nerfs cluniaux inférieurs"),
    "Sciatic_nerve.r": ("FMA22111", "right sciatic nerve", "Nerf sciatique"),
    # Tibial nerve
    "Tibial_nerve.r": ("FMA22109", "right tibial nerve", "Nerf tibial"),
    "Medial_sural_cutaneous_nerve.r": ("FMA45422", "right medial sural cutaneous nerve", "Nerf cutané sural médial"),
    "Sural_nerve.r": ("FMA45424", "right sural nerve", "Nerf sural"),
    "Sural_nerve,_Lateral_dorsal_cutaneous_nerve.r": ("FMA45426", "lateral dorsal cutaneous branch of right sural "
                                                      "nerve", "Nerf cutané dorsal latéral"),
    "Lateral_calcaneal_nerves.r": ("FMA45428", "lateral calcaneal branch of right sural nerve",
                                   "Rameaux calcanéens latéraux du nerf sural"),
    "Medial_calcaneal_branches_of_Tibial_nerve.r": ("FMA45432", "medial calcaneal branch of right tibial nerve",
                                                    "Rameaux calcanéens médiaux du nerf tibial"),
    "Medial_plantar_nerve.r": ("FMA45434", "right medial plantar nerve", "Nerf plantaire médial"),
    "Lateral_plantar_nerve.r": ("FMA45450", "right lateral plantar nerve", "Nerf plantaire latéral"),
    "Superficial_branch_of_Lateral_plantar_nerve.r": ("FMA45458", "superficial branch of right lateral plantar nerve",
                                                      "Rameau superficiel du nerf plantaire latéral"),
    "Deep_branch_of_Lateral_plantar_nerve.r": ("FMA80018", "deep branch of right lateral plantar nerve",
                                               "Rameau profond du nerf plantaire latéral"),
    "Common_plantar_digital_nerves.r": ("FMA75492", "set of common plantar digital nerves",
                                        "Nerfs digitaux plantaires communs"),
    "Proper_plantar_digital_branches_(Medial_plantar_nerve).r": ("FMA75493", "set of proper plantar digital nerves",
                                                                 "Nerfs digitaux plantaires propres"),
    "Proper_plantar_digital_branches_(Lateral_plantar_nerve).r": ("FMA75493", "set of proper plantar digital nerves",
                                                                  "Nerfs digitaux plantaires propres"),
    # Common fibular nerve
    "Common_fibular_nerve.r": ("FMA45357", "right common fibular nerve", "Nerf fibulaire commun"),
    "Lateral_sural_cutaneous_nerve.r": ("FMA45361", "right lateral sural cutaneous nerve", "Nerf cutané sural latéral"),
    "Superficial_fibular_nerve.r": ("FMA45363", "right superficial fibular nerve", "Nerf fibulaire superficiel"),
    "Medial_dorsal_cutaneous_nerve.r": ("FMA45365", "right medial dorsal cutaneous nerve", "Nerf cutané dorsal médial"),
    # Named "lateral" in Open3D, but it is the lateral terminal branch of the superficial fibular nerve
    # (it joins the medial dorsal cutaneous nerve and the dorsal digital nerves, not the sural nerve).
    "Lateral_dorsal_cutaneous_nerve.r": ("FMA45367", "right intermediate dorsal cutaneous nerve",
                                         "Nerf cutané dorsal intermédiaire"),
    "Deep_fibular_nerve.r": ("FMA45387", "right deep fibular nerve", "Nerf fibulaire profond"),
    "Medial_branch_of_deep_fibular_nerve.r": ("FMA45395", "medial terminal branch of right deep fibular nerve",
                                              "Rameau terminal médial du nerf fibulaire profond"),
    "Lateral_branch_of_deep_fibular_nerve.r": ("FMA45389", "lateral terminal branch of right deep fibular nerve",
                                               "Rameau terminal latéral du nerf fibulaire profond"),
    "Dorsal_digital_branches_of_superficial_fibular_nerve.r": ("FMA75491", "set of dorsal digital nerves of foot",
                                                               "Nerfs digitaux dorsaux du pied"),
    "Dorsal_digital_branches_of_deep_fibular_nerve.r": ("FMA75491", "set of dorsal digital nerves of foot",
                                                        "Nerfs digitaux dorsaux du pied"),
}
