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
    try: OFF27=json.load(open('data/officiel2627.json')).get('officiel',{})
    except Exception: OFF27={}
    DEPARTS={('SATO','Lautaro'),('LOUET','Sebastien'),('LANGLOIS','Xavier'),('CRENN-ALDEA','Julien')}   # quittent le club été 2026 — retirés de la Sportive uniquement
    # paires (joueur ACBB | adversaire) des journées MASCULINES phase 2, depuis site.json
    MPAIRS=set()
    try:
        _site=json.load(open('data/site.json'))['DATA']
        for _k,_pool in _site.items():
            if not _k.startswith('M'): continue
            _teams={t['name']:t for t in _pool['teams']}
            _acbb=[t for t in _pool['teams'] if t.get('acbb')]
            if not _acbb: continue
            for _j in _acbb[0]['journees']:
                _ot=_teams.get(_j.get('opponent'))
                _oj=[x for x in (_ot['journees'] if _ot else []) if x['journee']==_j['journee']]
                _opps=[fb.nrm((o.get('nom') or '')+(o.get('prenom') or '')) for o in (_oj[0]['players'] if _oj else [])]
                for _p in _j['players']:
                    if not _p.get('nom') or _p['nom']=='Joueur absent': continue
                    _pk=fb.nrm(_p['nom']+(_p.get('prenom') or ''))
                    for _o in _opps:
                        if _o: MPAIRS.add(_pk+'|'+_o)
    except Exception as e: print('  (MPAIRS indisponible:',e,')')
    def eq2stats(lic):
        """V/D en championnat par équipe MASCULIN phase 2 (simples), via paires joueur|adversaire."""
        try: prof=json.load(open('data/players/'+lic+'.json'))
        except Exception: return None
        me=fb.nrm((prof.get('nom') or '')+(prof.get('prenom') or ''))
        for comp in prof.get('competitions',[]):
            if comp.get('key')=='equipe':
                v=d=0
                for m in comp.get('matches',[]):
                    if not (m.get('date') or '').endswith('/2026'): continue
                    if (me+'|'+fb.nrm(m.get('opp') or '')) not in MPAIRS: continue
                    if m.get('won'): v+=1
                    else: d+=1
                n=v+d
                return {'n':n,'v':v,'pct':round(100*v/n)} if n else None
        return None
    out=[]
    for i,p in enumerate(players):
        lic=str(p.get('lic') or p.get('licence') or '')
        if not lic.isdigit(): continue
        if (p.get('nom'),p.get('prenom')) in DEPARTS: continue
        h=histo(lic); time.sleep(0.1)
        men=OFF27.get(lic, p.get('mensuel'))   # intersaison : base = officiel 2026/2027
        win=[{'l':e['lab'],'pt':e['pt']} for e in h[-WINDOW:]]
        # dernier point = OFFICIEL 2026/2027 (nouvelle saison publiée début juillet)
        if win and isinstance(men,(int,float)):
            win[-1]={'l':'Officiel 26/27','pt':round(men)}
        ys=[e['pt'] for e in win]
        if not isinstance(men,(int,float)): men=ys[-1] if ys else 500
        b=slope(ys)
        # tendance = variation ajustée (pente) sur la fenêtre : pente × (n-1) phases
        tend=round(b*(len(ys)-1)) if b is not None else 0
        out.append({'lic':lic,'nom':p.get('nom',''),'pre':p.get('prenom',''),'men':round(men),
                    'tend':tend,'spp':round(b,1) if b is not None else None,'h':win,'eq2':eq2stats(lic)})
        if (i+1)%50==0: print(f"  {i+1}/{len(players)} traités")
    # --- Mutations 2026/2027 (recrues) ---
    def mensuel_of(lic):
        lb=fb.get('xml_licence_b.php?licence='+lic); m=re.search(r'<point>(\d+)</point>',lb)
        return int(m.group(1)) if m else None   # officiel courant (base 26/27)
    MUT_LOOKUP=[('COHEN MELKA','Eytan','9258246'),('VERDIER','Mahé','9253816'),('SERGENT','Enzo','9540663'),
                ('INTINS','Arthur','9248896'),('STEMLER','Grégoire','9254353'),('INTINS','David','5412783'),
                ('DELORY','Virgile','9241720'),('BENCHAT','Marius','1421042'),('BOUDJADJA','Nassim','9265298')]
    MUT_HARD=[('GUNDOGDU','Kuzey',2090),('SHAMS','Navid',3320),('ARGUS','Daniel',1600),('PORTOKALLIS','Antonis',1500),('BOTELLA','Milo',500)]   # BOTELLA : pas encore sur FFTT, niveau à préciser
    for nom,pre,lic in MUT_LOOKUP:
        h=histo(lic); time.sleep(0.1); men=mensuel_of(lic)
        win=[{'l':e['lab'],'pt':e['pt']} for e in h[-WINDOW:]]
        if win and isinstance(men,(int,float)): win[-1]={'l':'Officiel 26/27','pt':round(men)}
        ys=[e['pt'] for e in win]; b=slope(ys)
        out.append({'lic':lic,'nom':nom,'pre':pre,'men':round(men) if isinstance(men,(int,float)) else (ys[-1] if ys else 500),
                    'tend':round(b*(len(ys)-1)) if b is not None else 0,'spp':round(b,1) if b is not None else None,'h':win,'mut':'2026/2027'})
    for nom,pre,men in MUT_HARD:
        out.append({'lic':None,'nom':nom,'pre':pre,'men':men,'tend':None,'spp':None,'h':[],'mut':'2026/2027'})
    print(f"  + {len(MUT_LOOKUP)+len(MUT_HARD)} mutations 2026/2027 ajoutées")
    out.sort(key=lambda r:r['nom'])
    payload={'built':datetime.datetime.now(datetime.timezone.utc).isoformat(),'window':WINDOW,'players':out}
    json.dump(payload, open("data/scoring.json","w"), ensure_ascii=False)
    with open("data/scoring.js","w",encoding="utf-8") as f:
        f.write("window.__SCORING="+json.dumps(payload,ensure_ascii=False)+";")
    nb=sum(1 for r in out if r['spp'] is not None)
    print(f"OK — {len(out)} joueurs ({nb} avec tendance calculable) -> data/scoring.json + scoring.js")

if __name__=='__main__': main()
