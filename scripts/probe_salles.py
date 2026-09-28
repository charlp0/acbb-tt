# -*- coding: utf-8 -*-
"""Sonde : l'API FFTT permet-elle de connaître, de façon FIABLE, l'adresse de la salle
où se joue un déplacement ?

Contexte : un capitaine (Guillaume Pierron, 27/09/2026) demande les adresses des salles
adverses. Nos adresses viennent aujourd'hui du PDF des poules CD92 : 44 déplacements
renseignés sur 77, et rien en régional ni en national. On veut savoir si l'API comble
le trou, et à quel point on peut s'y fier.

Trois questions :
  A. xml_club_b.php liste-t-il les clubs avec leur numéro ? (sinon, pas de clé de jointure)
  B. xml_club_detail.php donne-t-il salle + adresse + GPS ? (les champs du copie d'écran SPID)
  C. la rencontre elle-même (xml_chp_renc) porte-t-elle un lieu ? — c'est la seule source
     vraiment sûre : un club peut recevoir ailleurs que dans sa salle déclarée (notre F1
     joue bien une journée à Marly).
Le script n'écrit rien : il imprime, on lit le journal du workflow.
"""
import re, importlib.util

spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)

def tags(bloc):
    return re.findall(r'<([a-zA-Z0-9_]+)>(.*?)</\1>', bloc, re.S)

print("=" * 70)
print("A. xml_club_b.php?dep=92 — liste des clubs du 92")
r = fb.get("xml_club_b.php?dep=92")
print("   reponse : %d caracteres" % len(r))
blocs = re.findall(r'<club>(.*?)</club>', r, re.S)
print("   clubs trouves : %d" % len(blocs))
if blocs:
    print("   champs disponibles :", [k for k, _ in tags(blocs[0])])
    print("   exemple :", dict(tags(blocs[0])))
# on cherche un club precis dont on sait qu'on s'y deplace
num = None
for b in blocs:
    d = dict(tags(b))
    if 'MALAKOFF' in (d.get('nom') or '').upper():
        num = d.get('numero'); print("   MALAKOFF ->", d.get('numero'), d.get('nom')); break

print("=" * 70)
print("B. xml_club_detail.php — salle, adresse, GPS ?")
for n in [x for x in [num, '07920030', '07920112'] if x]:
    r = fb.get("xml_club_detail.php?club=%s" % n)
    print("   club %s : %d caracteres" % (n, len(r)))
    for b in re.findall(r'<club>(.*?)</club>', r, re.S)[:1]:
        for k, v in tags(b):
            if re.search(r'salle|adresse|ville|cp|latitude|longitude|nom|numero', k, re.I):
                print("      %-16s %s" % (k, (v or '')[:70]))
    if num: break

print("=" * 70)
print("C. la rencontre porte-t-elle un lieu ? (xml_chp_renc brut)")
# poule D2 phase 1 du 92, la meme que celle utilisee par fftt_site
r = fb.get("xml_chp_renc.php?action=equipe&auto=1&organisme_pere=&cx_poule=")
print("   sans parametres : %d caracteres" % len(r))
print("   apercu :", (r or '')[:400].replace("\n", " "))
print("=" * 70)
print("Conclusion a tirer a la lecture : si B donne salle+adresse+GPS, on peut remplir")
print("les 33 deplacements manquants, en precisant que c'est la salle DECLAREE du club")
print("et non le lieu confirme de la rencontre.")
