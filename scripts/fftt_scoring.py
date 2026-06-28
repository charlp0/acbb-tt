#!/usr/bin/env python3
"""Génère data/scoring.json + data/scoring.js pour la page scoring.html (aide compo, interne).
Score = mensuel actuel + k × tendance, où tendance = PENTE de régression linéaire sur les
4 dernières phases du classement OFFICIEL (via xml_histo_classement.php?numlic=...).
Identifiants via FFTT_ID / FFTT_PWD. Usage : python3 scripts/fftt_scoring.py
"""
import os, re, json, time, datetime, importlib.util
spec=importlib.util.spec_from_file_location("fb","scripts/fftt_build.py")
fb=importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
def tg(s,t):
    m=re.search('<'+t+'>(.*?)</'+t+'>',s,re.S); return m.group(1).strip() if m else ''

WINDOW=4   # nb de phases prises en compte pour la tendance

def histo(lic):
    """-> liste chronologique [{'an':int,'ph':int,'pt':int,'lab':'25/26 P2'}]"""
    r=fb.get('xml_histo_classement.php?numlic='+lic)
    out=[]
    for b in re.findall(r'<histo>(.*?)</histo>', r, re.S):
        sa=tg(b,'saison'); ph=tg(b,'phase'); pt=tg(b,'point')
        m=re.search(r'(\d{4})\s*/\s*(\d{4})', sa)
        if not m or not pt: continue
        try: pt=int(re.sub(r'\D','',pt))
        except: continue
        an=int(m.group(1)); p=int(ph) if ph.isdigit() else 1
        out.append({'an':an,'ph':p,'pt':pt,'lab':f"{m.group(1)[2:]}/{m.group(2)[2:]} P{p}"})
    out.sort(key=lambda e:(e['an'],e['ph']))
    return out

def slope(ys):
    """pente de régression linéaire (points/phase) sur ys ; None si <2 points."""
    n=len(ys)
    if n<2: return None
    xm=(n-1)/2; ym=sum(ys)/n
    num=sum((i-xm)*(ys[i]-ym) for i in range(n))
    den=sum((i-xm)**2 for i in range(n))
    return num/den if den else None

def main():
    if not fb.APPID or not fb.MDP: import sys; sys.exit("FFTT_ID / FFTT_PWD manquants")
    if os.environ.get('FFTT_SKIP_IF_FRESH')=='1':
        try:
            prev=json.load(open("data/scoring.json")).get('built','')[:10]
            if prev==datetime.datetime.now(datetime.timezone.utc).date().isoformat():
                print(f"scoring.json déjà à jour ({prev}) — skip."); return
        except Exception: pass
    idx=json.load(open('data/players_index.json'))
    players=idx if isinstance(idx,list) else idx.get('players',[])
    out=[]
    for i,p in enumerate(players):
        lic=str(p.get('lic') or p.get('licence') or '')
        if not lic.isdigit(): continue
        h=histo(lic); time.sleep(0.1)
        men=p.get('mensuel')
        win=[{'l':e['lab'],'pt':e['pt']} for e in h[-WINDOW:]]
        # dernier point = MENSUEL ACTUEL de la saison (pas l'officiel figé de la phase en cours,
        # qui ne reflète pas les matchs joués depuis le début de la phase)
        if win and isinstance(men,(int,float)):
            win[-1]={'l':'Mensuel actuel','pt':round(men)}
        ys=[e['pt'] for e in win]
        if not isinstance(men,(int,float)): men=ys[-1] if ys else 500
        b=slope(ys)
        # tendance = variation ajustée (pente) sur la fenêtre : pente × (n-1) phases
        tend=round(b*(len(ys)-1)) if b is not None else 0
        out.append({'nom':p.get('nom',''),'pre':p.get('prenom',''),'men':round(men),
                    'tend':tend,'spp':round(b,1) if b is not None else None,'h':win})
        if (i+1)%50==0: print(f"  {i+1}/{len(players)} traités")
    out.sort(key=lambda r:r['nom'])
    payload={'built':datetime.datetime.now(datetime.timezone.utc).isoformat(),'window':WINDOW,'players':out}
    json.dump(payload, open("data/scoring.json","w"), ensure_ascii=False)
    with open("data/scoring.js","w",encoding="utf-8") as f:
        f.write("window.__SCORING="+json.dumps(payload,ensure_ascii=False)+";")
    nb=sum(1 for r in out if r['spp'] is not None)
    print(f"OK — {len(out)} joueurs ({nb} avec tendance calculable) -> data/scoring.json + scoring.js")

if __name__=='__main__': main()
