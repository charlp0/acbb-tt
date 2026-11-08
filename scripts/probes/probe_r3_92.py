"""Sonde one-shot : exécute scripts/fftt_r3_92.py avec le dump JSON dans les logs (le workflow de sonde ne commite pas)."""
import os, runpy, sys
os.environ['R3_92_DUMP'] = '1'
sys.argv = ['fftt_r3_92.py']
runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'fftt_r3_92.py'), run_name='__main__')
