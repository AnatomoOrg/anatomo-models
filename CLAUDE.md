# Règles de travail (Claude)

## Pull requests : revue indépendante puis merge automatique

Toute PR ouverte par Claude suit ce cycle, sans attendre de validation manuelle :

1. **Revue indépendante obligatoire.** Avant tout merge, la PR est relue par un relecteur
   qui n'a pas écrit le code : un sous-agent Claude lancé à neuf (sans le contexte de
   l'auteur), qui lit le diff complet et cherche bugs, régressions, problèmes de licence
   et de sécurité. Chaque point bloquant est corrigé (ou réfuté par écrit sur la PR)
   avant le merge. La synthèse de la revue est postée en commentaire sur la PR.
2. **Merge automatique dès que la CI est verte.** Revue passée + CI verte sur le dernier
   commit + aucun conflit : Claude merge la PR lui-même. Si aucun workflow ne tourne sur
   la PR, la revue passée suffit.
3. Une CI rouge se corrige dans la PR ; on ne désactive jamais un test pour passer.
