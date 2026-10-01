"""Collecte normale ou échantillon de validation explicitement demandé par le workflow."""
import json
import os
import subprocess
import sys

args=[]
if os.environ.get('FFTT_SAMPLE')=='1':
    players=json.load(open('data/players_index.json'))
    sexes=json.load(open('data/sexes.json'))
    for sex in ('M','F'):
        group=[p for p in players if sexes.get(str(p['lic']))==sex and p.get('parties',0)>0]
        if group: args.append(str(max(group,key=lambda p:p.get('mensuel',0))['lic']))
    idle=next((p for p in players if not p.get('parties')),None)
    if idle: args.append(str(idle['lic']))
    if len(args)!=3:raise RuntimeError('Échantillon incomplet, aucun appel FFTT')
subprocess.run([sys.executable,'scripts/fftt_build.py',*args],check=True)
