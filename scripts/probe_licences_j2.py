# -*- coding: utf-8 -*-
"""Controle des licences des joueurs alignes en J2 qui n'ont pas joue la J1.
Demande de Charles le 02/10/2026, jour de la J2 : ces joueurs n'ont pas ete
"testes" par une premiere rencontre, une licence non validee passerait inapercue.
L'export du club du 17/09 est inutilisable (302 licences encore « non valide »
a cette date), seule l'API fait foi. Le script n'ecrit rien."""
import re, time, importlib.util
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
LICS = ['9238431', '9224819', '9250807', '9215542', '2710453', '9236487', '9241720', '287740', '6924091', '7824630', '9230121', '9261250', '9258960', '6221074', '9263353', '9211238', '9267050', '9261337', '9243175', '9259617', '7520188', '9261324']
def tags(s):
    return dict(re.findall(r'<([a-zA-Z0-9_]+)>(.*?)</\1>', s, re.S))
print("champs disponibles sur une fiche licence :")
r0 = fb.get("xml_licence_b.php?licence=%s" % LICS[0])
b0 = re.findall(r'<licence>(.*?)</licence>', r0, re.S)
print("   ", sorted(tags(b0[0]).keys()) if b0 else "aucune fiche")
print("=" * 78)
print("%-10s %-26s %-4s %-6s %-12s %s" % ("licence","joueur","type","certif","validation","categorie"))
for l in LICS:
    r = fb.get("xml_licence_b.php?licence=%s" % l); time.sleep(0.1)
    b = re.findall(r'<licence>(.*?)</licence>', r, re.S)
    if not b:
        print("%-10s *** AUCUNE FICHE RENVOYEE PAR LA FFTT ***" % l); continue
    d = tags(b[0])
    nom = (d.get('nom','') + ' ' + d.get('prenom','')).strip()
    print("%-10s %-26s %-4s %-6s %-12s %s" % (l, nom[:26], d.get('type',''), d.get('certif',''),
          d.get('validation',''), d.get('cat','')))

