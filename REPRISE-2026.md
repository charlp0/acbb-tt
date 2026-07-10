# 📋 Checklist de reprise — Saison 2026/2027 (septembre 2026)

Écrite le 09/07/2026, pendant l'intersaison. À dérouler dans l'ordre à la rentrée
(idéalement ~1 semaine avant la J1 du 18-19/09/2026).

## 0. Contexte figé de l'été
- L'API FFTT a basculé sur 2026/2027 début juillet → le championnat 25/26 n'est
  plus servi. Le site est en mode « Préparation » : récap 25/26 figé (archive
  `stats.html`), classements officiels 26/27 affichés (`data/officiel2627.json`).
- Robot en PAUSE : crons commentés dans `update-data.yml` et `check-freshness.yml`.
- Formulaire dispos phase 1 sur la home (clôture auto le 31/08, table Supabase
  `dispos_log`). Tags compos dans `tags_log`. Ping Supabase hebdo + keepalive
  mensuel actifs (ne pas y toucher).

## 1. Vérifier que l'API sert la saison 26/27
```bash
cd /tmp && git clone --depth 1 https://github.com/charlp0/acbb-tt.git acbb && cd acbb
FFTT_ID=... FFTT_PWD=... python3 - <<'PY'
import importlib.util,re
spec=importlib.util.spec_from_file_location("fb","scripts/fftt_build.py");fb=importlib.util.module_from_spec(spec);spec.loader.exec_module(fb)
eq=fb.get(f"xml_equipe.php?numclu={fb.CLUB}&type=A")
print(re.findall(r'<libequipe><!\[CDATA\[(.*?)\]\]>',eq))
PY
```
→ Doit lister les équipes 26/27 (M1 Pro B … M17, F). Sinon attendre.

## 2. Adapter les scripts à la nouvelle saison
- [ ] `scripts/fftt_site.py` : refaire le dict `META` (clé équipe → poule/division/
      classe CSS) avec les équipes 26/27 : M1=Pro B, M2=N1, M3=R1, M4=R2, M5=R3,
      M6-M7=PR, M8-M11=D1, M12-M17=D2 + équipes F. Adapter `ORDER` et le filtre
      `' - Phase 1'` (au lieu de Phase 2). ⚠️ Pro B/N1 = organisme fédéral, formats
      de feuille différents à vérifier (4 joueurs).
- [ ] `scripts/fftt_build.py` : `TEAMINFO`/`TEAMKEY` → nouvelles équipes ;
      remettre les compteurs/gardes-fous à zéro (`FFTT_FULL=1` au 1er run).
- [ ] `scripts/fftt_scoring.py` : re-basculer la base de `officiel2627.json` vers
      le MENSUEL courant (retirer OFF27, remettre `p['mensuel']` + label
      « Mensuel actuel ») ; vider `MUT_LOOKUP`/`MUT_HARD` (les mutations seront
      dans le roster) ; vider `DEPARTS` ; recalculer eq2stats sur la phase 1 26/27.
- [ ] `data/officiel2627.json` : devient obsolète quand le mensuel revit — retirer
      son affichage de `joueur.html`/`joueurs.html` (revenir au mensuel) OU le
      régénérer en `officiel` courant.

## 3. Réactiver l'automatisation
- [ ] Décommenter les blocs `schedule:` dans `.github/workflows/update-data.yml`
      et `check-freshness.yml`.
- [ ] Run manuel : `gh workflow run update-data.yml --repo charlp0/acbb-tt -f full=1`
- [ ] Vérifier les garde-fous : le run doit passer (>80 % des profils/équipes).
- [ ] Contrôler `data/meta.json` + le rendu des 3 pages d'équipe.

## 4. Bascule éditoriale du site (décision avec Charles)
- [ ] Home : retirer/archiver le bloc « Préparation » (calendrier + formulaire
      dispos clôturé) → remettre le mode « saison live » (sélecteur d'équipes,
      résultats). Le formulaire dispos pourra revivre pour la PHASE 2 (janvier).
- [ ] Onglet « Ch. Équipe 25/26 » : RESTE en archive telle quelle. Ajouter la
      saison courante (nouvelles pages ou revamp) — À DÉCIDER ENSEMBLE.
- [ ] Fiche joueur : « Récap 25/26 » devient historique ; la courbe repart sur
      la timeline 26/27 dès que le robot produit les nouveaux profils.
- [ ] Bannière récap saison + félicitations montées : à retirer ou archiver.

## 5. Sportive
- [ ] Tags compos : archiver la version « préparation » (le journal Supabase
      garde tout) ; les tags équipe/rôle restent valables pour la saison.
- [ ] Suivi des dispos : basculer les journées sur le calendrier réel si changé.
- [ ] Ré-évaluer le panneau « vs XXXX » (les moyennes adverses 25/26 restent
      la référence jusqu'aux premières journées 26/27).

## 6. Données à surveiller au 1er run
- Poules/divisions réelles vs prévision (Pro B !), formats des feuilles fédérales,
  joueurs mutés visibles dans le roster ACBB, nouveaux licenciés.

## Rappels sécurité
- Identifiants FFTT UNIQUEMENT en secrets GitHub (`FFTT_ID`/`FFTT_PWD`).
- La clé Supabase `sb_publishable_` est publique par design (RLS select+insert).

## Archivage 2026/2027 (leçon du 10/07/2026)
- [ ] Lancer `fftt_archive.py` pour la saison 26/27 en incluant AUSSI les
      divisions adjacentes (montée/descente : PN Messieurs, N3 si pertinent,
      D1 des départements voisins) — en 25/26 seules les divisions avec une
      équipe ACBB avaient été archivées, et R1M/PN M sont irrécupérables
      (l'API coupe la saison passée dès la bascule, même par cx_poule direct).
- [ ] Idéalement : archiver en FIN DE PHASE (janvier + juin), pas après la bascule.
