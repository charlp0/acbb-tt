# -*- coding: utf-8 -*-
"""Controle licence de TOUS les joueurs alignes en J2 (63), pas seulement ceux
qui n'avaient pas joue la J1. Demande de Charles le 02/10/2026.

Le champ qui fait foi est `validation` : la FFTT ne valide pas une licence tant
que l'obligation medicale n'est pas satisfaite, donc une licence validee couvre
aussi ce point. `certif` est reporte tel quel, sans interpretation : ses valeurs
(C / P / U) ne sont pas documentees ici, et Le Gall montre qu'un `certif` rempli
peut coexister avec une licence NON validee — ce n'est donc pas le bon critere.
Le script n'ecrit rien."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))  # scripts/ : fftt_site, fftt_brulages, fftt_quality (et fftt_build via importlib)
import re, time, importlib.util
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
JOUEURS = [['M10', '7838141'], ['M10', '287740'], ['M10', '6924091'], ['M10', '9411975'], ['M11', '7824630'], ['M11', '9526378'], ['M11', '9230121'], ['M11', '9234775'], ['M12', '9261250'], ['M12', '9258960'], ['M12', '9218870'], ['M13', '6221074'], ['M13', '9263353'], ['M13', '9211238'], ['M13', '9247334'], ['M14', '1611373'], ['M14', '9238309'], ['M14', '9262783'], ['M14', '9254385'], ['M15', '9267050'], ['M15', '7520384'], ['M15', '9265294'], ['M15', '9257684'], ['M16', '9261337'], ['M16', '9243175'], ['M16', '9260720'], ['M16', '9259617'], ['M17', '7520188'], ['M17', '9261324'], ['M17', '9261122'], ['M17', '9255399'], ['M2', '9238431'], ['M2', '1421042'], ['M2', '5973223'], ['M2', '9454825'], ['M3', '9267939'], ['M3', '9225667'], ['M3', '9258246'], ['M3', '9255025'], ['M4', '9261981'], ['M4', '9246007'], ['M4', '9252289'], ['M4', '7528733'], ['M5', '9224819'], ['M5', '9261979'], ['M5', '3325080'], ['M5', '9252971'], ['M6', '5412783'], ['M6', '9254370'], ['M6', '9250807'], ['M6', '7847253'], ['M7', '9252820'], ['M7', '9213785'], ['M7', '8015853'], ['M7', '9255609'], ['M8', '9227561'], ['M8', '9234489'], ['M8', '9215542'], ['M8', '926622'], ['M9', '2710453'], ['M9', '9236487'], ['M9', '9241720'], ['M9', '9254353']]
def tags(s):   # <licence> est imbriquee dans <licence> : lire sur la reponse entiere
    return dict(re.findall(r'<([a-zA-Z0-9_]+)>([^<]*)</\1>', s, re.S))
souci, ok = [], 0
lignes = []
for eq, lic in JOUEURS:
    r = fb.get("xml_licence_b.php?licence=%s" % lic); time.sleep(0.09)
    d = tags(r)
    nom = (d.get('nom','') + ' ' + d.get('prenom','')).strip()
    t, v, c, cl = d.get('type',''), d.get('validation',''), d.get('certif',''), d.get('nomclub','')
    bon = (t == 'T') and bool(v) and ('BOULOGNE BILLANCOURT' in cl.upper())
    lignes.append((eq, lic, nom, t, c, v, cl, bon))
    if bon: ok += 1
    else: souci.append((eq, lic, nom, t, c, v, cl))
print("%d joueurs controles · %d en regle · %d a verifier" % (len(JOUEURS), ok, len(souci)))
print("=" % () if False else "=" * 92)
if souci:
    print("A VERIFIER :")
    for eq, lic, nom, t, c, v, cl in souci:
        print("   %-4s %-9s %-26s type=%-2s certif=%-2s validation=%-11s %s" % (eq, lic, nom[:26], t or "VIDE", c or "-", v or "VIDE", cl))
else:
    print("aucun probleme")
print("=" * 92)
print("repartition du champ certif (pour information, non interprete) :")
from collections import Counter
print("   ", dict(Counter(x[4] or '(vide)' for x in lignes)))
print("croisement certif x categorie :")
print("   ", "voir le detail ci-dessous")
print("=" * 92)
for eq, lic, nom, t, c, v, cl, bon in lignes:
    print("%-4s %-9s %-26s type=%-2s certif=%-2s validation=%s" % (eq, lic, nom[:26], t or "VIDE", c or "-", v or "VIDE"))

