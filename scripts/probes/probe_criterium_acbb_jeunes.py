# -*- coding: utf-8 -*-
"""Sonde : toutes les parties de critérium des JEUNES du club (toutes divisions, D/R/N, garçons et filles)
pour un tour (env TOUR, défaut 1). Enveloppe de probe_criterium_acbb.py."""
import os, runpy
os.environ.setdefault('AGE', 'JEUNES'); os.environ.setdefault('GENRE', '*'); os.environ.setdefault('DIVS', '*'); os.environ.setdefault('NIVEAU', '*')
runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'probe_criterium_acbb.py'), run_name='__main__')
