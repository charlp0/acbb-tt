#!/usr/bin/env python3
"""ACBB TT — publie l'annuaire téléphonique dans le magasin protégé par jeton.

Avant le 26/09/2026 l'annuaire vivait chiffré dans le dépôt public
(data/phones.enc.json) et la page demandait un mot de passe pour le déchiffrer.
Depuis que l'espace sportive est protégé par des liens d'accès personnels, ce
mot de passe faisait double emploi : l'annuaire est désormais stocké dans
scenarios_log (slot « annuaire »), table sous RLS que seule la fonction Edge
lit, et uniquement pour un porteur de lien sportive. Plus aucun numéro de
téléphone n'est publié sur le site.

Usage :  python3 scripts/push_annuaire.py [chemin/vers/annuaire.json]
Défaut : ~/Documents/Claude/Context/acbb-phones-titulaires.json (hors dépôt).
Clé service_role lue dans ~/Documents/Claude/Context/.secrets.env, jamais affichée.
Le fichier source attend { "phones": {"NOM|PRENOM": "0612…"}, "extra": {...} } ;
les clés sont renormalisées ici comme le fait la page (accents retirés, A-Z0-9).
"""
import json, os, re, sys, unicodedata, urllib.request, datetime

SB = "https://vhhmageufrcenruywawg.supabase.co"
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
    "~/Documents/Claude/Context/acbb-phones-titulaires.json")
SECRETS = os.path.expanduser("~/Documents/Claude/Context/.secrets.env")

def cle(s):
    s = unicodedata.normalize('NFD', str(s or '')).encode('ascii', 'ignore').decode().upper()
    return re.sub(r'[^A-Z0-9]', '', s)

def normalise(d):
    out = {}
    for k, v in (d or {}).items():
        n, _, p = str(k).partition('|')
        out[cle(n) + '|' + cle(p)] = v
    return out

key = ''
for ligne in open(SECRETS, encoding='utf-8'):
    if ligne.startswith('SUPA_SERVICE_KEY='):
        key = ligne.split('=', 1)[1].strip().strip('"').strip("'")
if not key:
    sys.exit("SUPA_SERVICE_KEY absent de " + SECRETS)

raw = json.load(open(SRC, encoding='utf-8'))
tags = {
    'phones': normalise(raw.get('phones')),
    'extra': normalise(raw.get('extra')),
    'built': datetime.date.today().isoformat(),
}
tags['n'] = len(tags['phones'])
corps = json.dumps({'slot': 'annuaire', 'author': 'annuaire', 'tags': tags}).encode('utf-8')
req = urllib.request.Request(SB + '/rest/v1/scenarios_log', data=corps, method='POST', headers={
    'apikey': key, 'Authorization': 'Bearer ' + key,
    'Content-Type': 'application/json', 'Prefer': 'return=representation'})
with urllib.request.urlopen(req) as r:
    ligne = json.load(r)[0]
print("annuaire publié · ligne %s · %d numéros, %d notes complémentaires"
      % (ligne['id'], tags['n'], len(tags['extra'])))
