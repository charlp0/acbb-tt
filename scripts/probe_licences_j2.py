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
    """La reponse de xml_licence_b imbrique une balise <licence> DANS <licence> : decouper sur
    l'enveloppe coupe au mauvais endroit. On lit donc les champs directement sur la reponse,
    qui ne porte qu'une seule fiche puisqu'on interroge licence par licence."""
    return dict(re.findall(r'<([a-zA-Z0-9_]+)>([^<]*)</\1>', s, re.S))
r0 = fb.get("xml_licence_b.php?licence=%s" % LICS[0])
print("champs disponibles sur une fiche licence :")
print("   ", sorted(tags(r0).keys()))
print("   exemple brut :", " | ".join("%s=%s" % kv for kv in sorted(tags(r0).items()))[:300])
print("=" * 86)
print("%-10s %-26s %-5s %-7s %-12s %-5s %s" % ("licence","joueur","type","certif","validation","cat","club"))
for l in LICS:
    r = fb.get("xml_licence_b.php?licence=%s" % l); time.sleep(0.1)
    d = tags(r)
    if not d.get('nom'):
        print("%-10s *** AUCUNE FICHE RENVOYEE PAR LA FFTT ***" % l); continue
    nom = (d.get('nom','') + ' ' + d.get('prenom','')).strip()
    print("%-10s %-26s %-5s %-7s %-12s %-5s %s" % (l, nom[:26], d.get('type',''), d.get('certif',''),
          d.get('validation',''), d.get('cat',''), d.get('nomclub','')[:24]))
