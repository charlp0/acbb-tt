# -*- coding: utf-8 -*-
"""Sonde : valeurs brutes de <cat> (et <echelon>, <type>) renvoyées par xml_licence_b pour tout le club.
Objectif : savoir comment la FFTT code les vétérans (V1..V5 ? autre ?). Lecture seule."""
import os, re, sys, importlib.util, json, collections, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
idx = json.load(open('data/players_index.json'))
cats = collections.Counter(); ex = {}
for i, p in enumerate(idx):
    x = fb.get('xml_licence_b.php?licence=%s' % p['lic'])
    c = fb.tag(x, 'cat'); cats[c] += 1
    ex.setdefault(c, []).append('%s %s %s (%s pts, type=%s echelon=%s)' % (p['lic'], p['nom'], p['prenom'], fb.tag(x, 'point'), fb.tag(x, 'type'), fb.tag(x, 'echelon')))
    if i % 100 == 0: print('  …', i); time.sleep(0.05)
print('Valeurs brutes de <cat> :', dict(cats))
for c, l in ex.items(): print('  cat=%r → %d joueurs, ex. %s' % (c, len(l), ' | '.join(l[:3])))
