# -*- coding: utf-8 -*-
"""Sonde brute (lecture seule) : retrouver les divisions du critérium fédéral CD92 2026-27 sans
xml_epreuve (bloqué). 1) ids de division des équipes (liendivision) pour cadrer la plage ;
2) epr est-il obligatoire ? ; 3) balayage de res_division autour de la plage avec action=classement."""
import os, re, sys, html, importlib.util, requests, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
def raw(ep, pause=0.12):
    url = fb.BASE + ep + ("&" if "?" in ep else "?") + fb.auth()
    for _ in range(2):
        try:
            r = requests.get(url, timeout=25); r.encoding = 'ISO-8859-1'; time.sleep(pause); return r.status_code, r.text
        except Exception as e: err = str(e); time.sleep(1)
    return 0, err
def tg(b, t):
    m = re.search('<'+t+'>(.*?)</'+t+'>', b, re.S); return m.group(1).strip() if m else ''
sq = lambda s: re.sub(r'\s+', ' ', s)
st, r = raw('xml_equipe.php?numclu=%s&type=A' % fb.CLUB)
ids = {}
for b in re.findall(r'<equipe>(.*?)</equipe>', r, re.S):
    lien = html.unescape(re.sub(r'<!\[CDATA\[|\]\]>', '', tg(b, 'liendivision')))
    m = re.search(r'D1=(\d+)', lien); o = re.search(r'organisme_pere=(\d+)', lien)
    if m: ids.setdefault(o.group(1) if o else '?', []).append((int(m.group(1)), tg(b, 'libdivision')[:45], lien[:80]))
for o, v in ids.items():
    v.sort(); print('organisme', o, ':', len(v), 'divisions ; ids', v[0][0], '→', v[-1][0]); 
    for x in v[:3]: print('    ', x)
d92 = sorted(x[0] for x in ids.get('116', []))
if not d92: print('pas de division D92 trouvée'); sys.exit(0)
print('\n== epr obligatoire ?')
for ep in ['xml_result_indiv.php?action=classement&res_division=%d' % d92[0],
           'xml_result_indiv.php?action=classement&epr=0&res_division=%d' % d92[0],
           'xml_result_indiv.php?action=tableau&epr=0&res_division=%d' % d92[0],
           'xml_result_equ.php?action=classement&auto=1&D1=%d&organisme_pere=116' % d92[0]]:
    st, r = raw(ep); print('  ', ep, '→', st, sq(r)[:200])
lo, hi = d92[0] - 500, d92[-1] + 500
print('\n== balayage res_division %d → %d (action=classement, epr=0) — seules les réponses non vides sont affichées' % (lo, hi))
hits = 0; t0 = time.time()
for div in range(lo, hi + 1):
    st, r = raw('xml_result_indiv.php?action=classement&epr=0&res_division=%d' % div, pause=0.05)
    if st != 200: print('  ', div, '→ HTTP', st, sq(r)[:120]); continue
    if '<liste/>' in r or len(r) < 80: continue
    hits += 1; print('  HIT', div, '→', sq(r)[:400])
    if hits >= 40: print('  (arrêt à 40 hits)'); break
print('fin du balayage en %.0f s, %d hits' % (time.time() - t0, hits))
