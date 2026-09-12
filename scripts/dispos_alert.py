# -*- coding: utf-8 -*-
"""Alerte dispos : détecte les saisies nouvelles/modifiées dans dispos_log depuis le dernier passage,
signale celles qui touchent une compo enregistrée (scenarios_log j1..j7) d'une journée à venir,
et écrit un bloc prêt à coller dans WhatsApp. État : data/dispos_alert_state.json ({last_id}).
Usage : python3 scripts/dispos_alert.py [--since ID] [--out alert.md]  -> exit 0, imprime CHANGES=<n> sur la dernière ligne."""
import json, re, sys, unicodedata, urllib.request, datetime, os
SB = "https://vhhmageufrcenruywawg.supabase.co"; PUB = "sb_publishable_NuRpgtxqVQ87R6K8txw57Q_oBUt4qay"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def get(p): return json.load(urllib.request.urlopen(urllib.request.Request(SB + p, headers={'apikey': PUB}), timeout=30))
args = sys.argv[1:]; since = None; out_path = 'alert.md'
if '--since' in args: since = int(args[args.index('--since') + 1])
if '--out' in args: out_path = args[args.index('--out') + 1]
state_path = os.path.join(ROOT, 'data/dispos_alert_state.json')
state = json.load(open(state_path)) if os.path.exists(state_path) else {'last_id': 0}
if since is None: since = int(state.get('last_id', 0))
rows = get("/rest/v1/dispos_log?select=id,licence,prenom,nom,dispos,n,created_at&order=id.asc")
rows = [r for r in rows if r['licence'] and not re.match(r'^(TEST|0000)', str(r['licence']), re.I)]
sc = {p['lic']: p for p in json.load(open(os.path.join(ROOT, 'data/scoring.json')))['players']}
tags = get("/rest/v1/tags_log?select=tags&order=id.desc&limit=1")[0]['tags']
poules = json.load(open(os.path.join(ROOT, 'data/poules2627.json')))
nk = lambda s: re.sub(r'[^A-Z0-9]', '', unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper())
bysn = {}
for p in sc.values(): bysn['SN-' + nk(p['nom']) + '-' + nk(p['pre'])] = p; bysn['SN-' + nk(p['pre']) + '-' + nk(p['nom'])] = p
def canon(r):
    raw = str(r['licence'])
    if raw.startswith('SN-'): m = bysn.get(raw); return str(m['lic']) if m else raw
    return raw
def team(k):
    t = tags.get(k) or {}
    if t.get('e'): return t['e']
    if t.get('r') == 'R' and t.get('d'): return 'pool ' + t['d']
    return None
def name(r, k): p = sc.get(k); return (p['pre'] + ' ' + p['nom']) if p else f"{r['prenom']} {r['nom']}".strip()
def js(d): return ''.join('✓' if (d or {}).get('j' + str(i)) else '✗' for i in range(1, 8))
def dispo(d, j): return bool((d or {}).get('j' + str(j)))
# compos enregistrées des journées à venir
today = datetime.date.today()
def pdate(s):
    m = re.match(r'(\d\d)/(\d\d)/(\d{4})', s or ''); return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None
jdates = {}
for j in range(1, 8):
    ds = [pdate(c['date']) for q in poules['poules'] for c in q['cal'] if c['j'] == j and pdate(c['date'])]
    jdates[j] = min(ds) if ds else None
compos = {}
for r in get("/rest/v1/scenarios_log?select=slot,tags&slot=in.(j1,j2,j3,j4,j5,j6,j7)&order=id.desc"):
    j = int(r['slot'][1:])
    if j in compos or not jdates.get(j) or jdates[j] < today: continue
    compos[j] = {t: v for t, v in (r['tags'] or {}).items() if t != '_meta'}
def aligned(k):
    out = []
    for j, c in sorted(compos.items()):
        for t, v in c.items():
            if k in (v.get('p') or []): out.append((j, t))
    return out
hist = {}
for r in rows: hist.setdefault(canon(r), []).append(r)
new_rows = [r for r in rows if r['id'] > since]
changes = []
for k, rs in hist.items():
    rec = [r for r in rs if r['id'] > since]
    if not rec: continue
    last = rec[-1]; prev = [r for r in rs if r['id'] <= since]
    before = prev[-1]['dispos'] if prev else None; after = last['dispos'] or {}
    roles = after.get('roles', []); roles_b = (before or {}).get('roles') if before else None
    if before is None: kind = 'new'
    elif js(before) == js(after) and roles_b == roles: kind = 'same'
    else: kind = 'mod'
    impacts = []
    for j, t in aligned(k):
        if not dispo(after, j) and (before is None or dispo(before, j)) or 'N' in roles:
            impacts.append(f"aligné en {t} pour la J{j} ({jdates[j].strftime('%d/%m')})")
    changes.append({'k': k, 'name': name(last, k), 'team': team(k) or '—', 'kind': kind, 'before': js(before) if before else None, 'after': js(after), 'roles': roles, 'n': after.get('n', last.get('n')), 'impacts': impacts, 'at': last['created_at']})
real = [c for c in changes if c['kind'] != 'same']
if not real:   # rien de nouveau (ou seulement des ressaisies identiques) : on avance le curseur sans alerter
    if new_rows: json.dump({'last_id': new_rows[-1]['id'], 'at': datetime.datetime.utcnow().isoformat() + 'Z'}, open(state_path, 'w'))
    print('CHANGES=0'); sys.exit(0)
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=2))).strftime('%d/%m %Hh%M')
def rolestr(r): return {'T': 'titulaire', 'R': 'remplaçant', 'N': 'ne veut pas jouer', 'REF': 'capitaine'}.get(r, r)
wa = [f"📋 *Dispos — MAJ du {now}*"]
imp = [c for c in changes if c['impacts']]
if imp:
    wa.append(''); wa.append('⚠️ *Impact sur les compos enregistrées*')
    for c in imp: wa.append(f"• {c['name']} ({c['team']}) : {c['after']}" + (" · ne veut pas jouer" if 'N' in c['roles'] else '') + " — " + ' ; '.join(c['impacts']))
mods = [c for c in changes if c['kind'] == 'mod' and not c['impacts']]
if mods:
    wa.append(''); wa.append('✏️ *Modifications*')
    for c in mods: wa.append(f"• {c['name']} ({c['team']}) : {c['before']} → {c['after']}" + (" · " + ', '.join(rolestr(x) for x in c['roles']) if c['roles'] != ['T'] else ''))
news = [c for c in changes if c['kind'] == 'new' and not c['impacts']]
if news:
    wa.append(''); wa.append('🆕 *Nouvelles saisies*')
    for c in news: wa.append(f"• {c['name']} ({c['team']}) : {c['after']}" + (" · " + ', '.join(rolestr(x) for x in c['roles']) if c['roles'] != ['T'] else ''))
same = [c for c in changes if c['kind'] == 'same']
if same:
    wa.append(''); wa.append('🔁 Ressaisies sans changement : ' + ', '.join(c['name'] for c in same))
wa.append(''); wa.append('_✓✗ = J1→J7 · détail sur team.acbb-tt.fr/sportive/suivi-dispos.html_')
wa_txt = '\n'.join(wa)
md = f"**{len(real)} changement(s)**, {len(same)} ressaisie(s) identique(s), {len(new_rows)} ligne(s) lues (id {since + 1} → {new_rows[-1]['id']}).\n\nBloc à coller dans WhatsApp :\n\n```\n{wa_txt}\n```\n"
open(out_path, 'w').write(md)
json.dump({'last_id': new_rows[-1]['id'], 'at': datetime.datetime.utcnow().isoformat() + 'Z'}, open(state_path, 'w'))
print(wa_txt); print(f"IMPACTS={len(imp)}"); print(f"CHANGES={len(real)}")
