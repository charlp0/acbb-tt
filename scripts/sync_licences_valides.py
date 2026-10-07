#!/usr/bin/env python3
"""Aligne la table `licences_valides` sur l'effectif FFTT du club (data/players_index.json).

La table est la liste des licences autorisées à s'identifier (dispos, Championnat de Paris,
critérium) ; le déclencheur `dispos_guard` et la fonction Edge la consultent. Elle avait été
remplie une fois à la bascule (16/09/2026) et plus jamais : les 31 licenciés arrivés depuis
étaient refusés (« licence inconnue »), dont un jeune du critérium le 07/10. Ce script
AJOUTE les licences manquantes ; il ne retire jamais rien (un départ du club se traite à la
main). Lancé par « Mise à jour données FFTT » après la reconstruction de players_index.json.

Usage : python3 scripts/sync_licences_valides.py [--dry-run]   (SUPA_SERVICE_KEY dans l'environnement)
"""
import json, os, sys, urllib.request

SB = 'https://vhhmageufrcenruywawg.supabase.co'
KEY = os.environ.get('SUPA_SERVICE_KEY', '').strip()

def req(path, method='GET', body=None, prefer=None):
    h = {'apikey': KEY, 'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'}
    if prefer: h['Prefer'] = prefer
    r = urllib.request.Request(SB + path, method=method, data=None if body is None else json.dumps(body).encode(), headers=h)
    with urllib.request.urlopen(r, timeout=60) as x:
        raw = x.read()
        return json.loads(raw) if raw else None

def main():
    dry = '--dry-run' in sys.argv
    if not KEY: sys.exit('SUPA_SERVICE_KEY absent')
    effectif = sorted({str(p['lic']) for p in json.load(open('data/players_index.json')) if p.get('lic') and str(p['lic']).isdigit()})
    valides = {r['licence'] for r in req('/rest/v1/licences_valides?select=licence&limit=5000')}
    manquantes = [l for l in effectif if l not in valides]
    print(f"effectif FFTT : {len(effectif)} · licences valides : {len(valides)} · manquantes : {len(manquantes)}")
    if not manquantes or dry:
        return
    req('/rest/v1/licences_valides', 'POST', [{'licence': l} for l in manquantes], prefer='resolution=ignore-duplicates,return=minimal')
    req('/rest/v1/journal', 'POST', {'acteur': 'robot', 'role': 'sportive', 'action': 'licences_valides_sync',
                                    'details': {'ajoutees': len(manquantes), 'source': 'data/players_index.json'}}, prefer='return=minimal')
    print(f"{len(manquantes)} licence(s) ajoutée(s) à licences_valides")   # jamais les numéros : journal d'Actions public

if __name__ == '__main__':
    main()
