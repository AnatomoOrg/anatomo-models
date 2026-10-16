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
| 3.0 (2011-09-15) | `BodyParts3D_3.0_obj_95` | Os et muscles du membre supérieur (maillages plus denses) |

Les identifiants de structures (`FMA…`) viennent de la Foundational Model of Anatomy, telle que
reprise par BodyParts3D.

## Modifications apportées

Faites par le projet Anatomo avec le code de `pipeline/` :

- sélection des structures (membre supérieur droit pour `upper_limb`, tout le corps pour `full_body`) ;
- regroupement des fichiers éléments par concept FMA ;
- recalage des maillages 3.0 dans le repère 4.0 (translation constante) ;
- fusion des sommets dupliqués, décimation ;
- changement de repère et d'unité (mm → m, axe vertical en +Y) ;
- fusion des maillages par système anatomique, avec un indice de structure par sommet ;
- ajout de noms français (`data/fr_names.json`) et de repères osseux calculés (humérus).

Les modèles dérivés sont distribués sous la même licence, CC BY-SA 2.1 JP (voir `LICENSE`).
Les fichiers glb portent l'attribution dans `asset.copyright`.

## Pour les applications qui utilisent ces modèles

Afficher l'attribution ci-dessus, la licence (avec son lien) et un lien vers ce dépôt, où les
modèles et le code qui les produit restent librement accessibles. Ne pas chiffrer ni verrouiller
les fichiers de modèles distribués.
