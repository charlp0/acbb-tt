# -*- coding: utf-8 -*-
"""Sonde : existe-t-il un point d'entrée FFTT qui rende DÉJÀ le bilan agrégé
(victoires, défaites, performances, contres) d'un licencié ?

Si oui, inutile d'agréger nous-mêmes. Sinon, la liste des parties reste la source
et l'agrégation se fait chez nous. On teste les noms plausibles et on regarde aussi
si xml_licence_b cache un champ de bilan qu'on aurait manqué.
"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))  # scripts/ : fftt_site, fftt_brulages, fftt_quality (et fftt_build via importlib)
import re, time, importlib.util
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)

LIC = '7824630'
CANDIDATS = [
    "xml_licence.php?licence=%s" % LIC,
    "xml_licence_b.php?licence=%s" % LIC,
    "xml_joueur.php?licence=%s" % LIC,
    "xml_bilan.php?licence=%s" % LIC,
    "xml_histo_classement.php?numlic=%s" % LIC,
    "xml_statistique.php?licence=%s" % LIC,
    "xml_perf.php?licence=%s" % LIC,
]
for ep in CANDIDATS:
    r = fb.get(ep); time.sleep(0.2)
    nom = ep.split('?')[0]
    if not r:
        print("%-34s AUCUNE REPONSE (point d'entree inexistant)" % nom); continue
    champs = sorted(set(re.findall(r'<([a-zA-Z0-9_]+)>', r)))
    bilan = [c for c in champs if re.search(r'vict|defa|perf|contre|bilan|nbv|nbd|stat', c, re.I)]
    print("%-34s %5d car. · champs : %s" % (nom, len(r), ', '.join(champs[:18])))
    print("%-34s champs de bilan : %s" % ('', bilan or 'AUCUN'))
