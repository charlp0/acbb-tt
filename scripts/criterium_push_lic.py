# -*- coding: utf-8 -*-
"""Dépose la table des licences du critérium dans Supabase, pour que le workflow
des bilans puisse interroger la FFTT sans que ces licences passent par le dépôt.

Les convertisseurs produisent data/_criterium_lic.json (privé, ignoré par git) :
{ "<id du groupe>": { "<position>": "<licence>" } }. Ce fichier ne contient que ce
que le PDF du comité publie déjà, mais il n'a rien à faire dans un dépôt public.
On le pousse donc dans scenarios_log, table sous RLS que seule la clé service lit.

Usage : python3 scripts/criterium_push_lic.py [tour]
Clé service_role lue dans ~/Documents/Claude/Context/.secrets.env, jamais affichée.
"""
import json, os, sys, urllib.request

SB = "https://vhhmageufrcenruywawg.supabase.co"
SRC = 'data/_criterium_lic.json'
SECRETS = os.path.expanduser("~/Documents/Claude/Context/.secrets.env")

def cle():
    for l in open(SECRETS, encoding='utf-8'):
        if l.startswith('SUPA_SERVICE_KEY='):
            return l.split('=', 1)[1].strip().strip('"').strip("'")
    sys.exit('SUPA_SERVICE_KEY absent de ' + SECRETS)

def main():
    tour = sys.argv[1] if len(sys.argv) > 1 else '1'
    if not os.path.exists(SRC):
        sys.exit('%s introuvable — lance d\'abord les convertisseurs' % SRC)
    table = json.load(open(SRC))
    k = cle()
    corps = json.dumps({'slot': 'criterium_lic', 'author': 'criterium tour ' + tour,
                        'tags': {'tour': tour, 'lic': table}}, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(SB + '/rest/v1/scenarios_log', data=corps, method='POST', headers={
        'apikey': k, 'Authorization': 'Bearer ' + k,
        'Content-Type': 'application/json', 'Prefer': 'return=representation'})
    with urllib.request.urlopen(req) as r:
        ligne = json.load(r)[0]
    print('licences déposées · ligne %s · %d groupes, %d licences'
          % (ligne['id'], len(table), sum(len(v) for v in table.values())))

if __name__ == '__main__':
    main()
