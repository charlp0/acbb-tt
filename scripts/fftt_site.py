#!/usr/bin/env python3
"""Génère data/site.json (DATA + STANDINGS) pour les pages d'équipe (accueil/equipe/stats),
depuis l'API FFTT live -> ces pages deviennent data-driven (fini les données figées en dur).
Identifiants via FFTT_ID / FFTT_PWD. Usage : python3 scripts/fftt_site.py
"""
import os, re, html, json, time, datetime, importlib.util
spec=importlib.util.spec_from_file_location("fb","scripts/fftt_build.py")
fb=importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
def tg(s,t):
    m=re.search('<'+t+'>(.*?)</'+t+'>',s,re.S); return m.group(1).strip() if m else ''

# métadonnées figées par équipe (pool/level/levelClass) — reproduit le contrat existant
META={
 'F1':("L08_PN Poule 2","Pré-Nationale","level-pn"),'F2':("L08_R1 Poule 3","Régional 1","level-r1"),
 'F3':("D92 Pré-Régionale Poule 1","Pré-Régional","level-prereg"),'M2':("FED_Nationale 2 Poule 3","Nationale 2","level-nat2"),
 'M3':("L08_R2 Poule 4","Régional 2","level-regional"),'M4':("L08_R3 Poule 11","Régional 3","level-regional"),
 'M5':("L08_R3 Poule 4","Régional 3","level-regional"),'M6':("D92 Pré-Régionale Poule 3","Pré-Régional","level-prereg"),
 'M7':("D92 Pré-Régionale Poule 2","Pré-Régional","level-prereg"),'M8':("D92 Pré-Régionale Poule 4","Pré-Régional","level-prereg"),
 'M9':("D92 Pré-Régionale Poule 1","Pré-Régional","level-prereg"),'M10':("D92 D1 Poule 3","Départemental 1","level-d1"),
 'M11':("D92 D1 Poule 4","Départemental 1","level-d1"),'M12':("D92 D2 Poule 8","Départemental 2","level-d2"),
 'M13':("D92 D2 Poule 11","Départemental 2","level-d2"),'M14':("D92 D2 Poule 12","Départemental 2","level-d2"),
 'M15':("D92 D2 Poule 10","Départemental 2","level-d2"),'M16':("D92 D2 Poule 5","Départemental 2","level-d2"),
 'M17':("D92 D2 Poule 4","Départemental 2","level-d2"),
}
ORDER=['F1','F2','F3','M2','M3','M4','M5','M6','M7','M8','M9','M10','M11','M12','M13','M14','M15','M16','M17']
MOISFR={1:'janv.',2:'févr.',3:'mars',4:'avr.',5:'mai',6:'juin',7:'juil.',8:'août',9:'sept.',10:'oct.',11:'nov.',12:'déc.'}
def datefr(d):
    try: j,m,a=d.split('/'); return f"{int(j)} {MOISFR[int(m)]} {a}"
    except: return d
def is_acbb(n): return 'BOULOGNE BILLAN' in (n or '')
def splitnom(full):
    full=(full or '').strip()
    if not full or full.lower().startswith('absent'): return ('Joueur absent','')
    parts=full.split();
    return (' '.join(parts[:-1]), parts[-1]) if len(parts)>1 else (full,'')
def parse_cls(x):
    x=x or ''
    m=re.match(r'\s*N\d+', x)
    if m: return m.group(0).strip()
    d=re.search(r'\d+', x); return int(d.group(0)) if d else 'x'

def fetch_renc(lien):
    """feuille -> { nrm(nom équipe) : (lineup, doubles) }. La feuille a SA propre orientation
    equa/equb : on renvoie donc les compos indexées par nom d'équipe (robuste aux inversions)."""
    r=fb.get("xml_chp_renc.php?"+lien)
    ea,eb=tg(r,'equa'),tg(r,'equb')   # noms d'équipe DE LA FEUILLE (xja appartient à ea, xjb à eb)
    A={}; B={}
    for jb in re.findall(r'<joueur>(.*?)</joueur>', r, re.S):
        na,ca,nb,cb=tg(jb,'xja'),tg(jb,'xca'),tg(jb,'xjb'),tg(jb,'xcb')
        if na and ' et ' not in na: A.setdefault(na,{'nom':splitnom(na)[0],'prenom':splitnom(na)[1],'cls':parse_cls(ca),'vic':0})
        if nb and ' et ' not in nb: B.setdefault(nb,{'nom':splitnom(nb)[0],'prenom':splitnom(nb)[1],'cls':parse_cls(cb),'vic':0})
    dA=dB=0
    for p in re.findall(r'<partie>(.*?)</partie>', r, re.S):
        ja,jbn=tg(p,'ja'),tg(p,'jb'); sa,sb=tg(p,'scorea'),tg(p,'scoreb')
        awin = sa.isdigit() and sb.isdigit() and int(sa)>int(sb)
        bwin = sa.isdigit() and sb.isdigit() and int(sb)>int(sa)
        if ' et ' in ja or ' et ' in jbn:           # double
            if awin: dA+=1
            elif bwin: dB+=1
            continue
        if awin and ja in A: A[ja]['vic']+=1
        elif bwin and jbn in B: B[jbn]['vic']+=1
    return {fb.nrm(ea):(list(A.values()),dA), fb.nrm(eb):(list(B.values()),dB)}

def build_pool(key, cx, d1, org):
    cal=fb.get(f"xml_result_equ.php?cx_poule={cx}&D1={d1}&organisme_pere={org}")
    # rencontres -> par équipe, ses journées
    teams={}   # name -> {name, journees:[]}
    acbb_cal={}
    for t in re.findall(r'<tour>(.*?)</tour>', cal, re.S):
        ea,eb=tg(t,'equa'),tg(t,'equb')
        if not(ea and eb): continue
        jn=re.search(r'tour\s*n°?\s*(\d+)', tg(t,'libelle')); jn=int(jn.group(1)) if jn else 0
        date=datefr(tg(t,'datereelle') or tg(t,'dateprevue'))
        sa,sb=tg(t,'scorea'),tg(t,'scoreb')
        played = sa.isdigit() and sb.isdigit()
        lm=re.search(r'<lien><!\[CDATA\[(.*?)\]\]>',t)
        la,lb,da,db=([],[],0,0)
        if lm:
            comps=fetch_renc(html.unescape(lm.group(1))); time.sleep(0.2)
            la,da=comps.get(fb.nrm(ea),([],0))   # rattachement par NOM (pas par position feuille)
            lb,db=comps.get(fb.nrm(eb),([],0))
        def tpts(lst): return sum(p['cls'] for p in lst if isinstance(p['cls'],int)) or None
        # journée côté A
        jA={'journee':jn,'date':date,'players':la,'doubles':da,'opponent':eb}
        jB={'journee':jn,'date':date,'players':lb,'doubles':db,'opponent':ea}
        if played:
            jA['match_score']=int(sa); jA['opp_score']=int(sb)
            jB['match_score']=int(sb); jB['opp_score']=int(sa)
            tpa,tpb=tpts(la),tpts(lb)
            if tpa: jA['team_pts']=tpa
            if tpb: jB['team_pts']=tpb
        teams.setdefault(ea,{'name':ea,'journees':[]})['journees'].append(jA)
        teams.setdefault(eb,{'name':eb,'journees':[]})['journees'].append(jB)
        # calendrier ACBB + marquage adverses
        if is_acbb(ea): acbb_cal[jn]={'opponent':eb,'domext':'Dom'}; teams[eb].setdefault('_acbbJ',jn); teams[eb]['_acbbDom']='Ext'
        if is_acbb(eb): acbb_cal[jn]={'opponent':ea,'domext':'Ext'}; teams[ea].setdefault('_acbbJ',jn); teams[ea]['_acbbDom']='Dom'
    # finalise teams
    out=[]
    for n,t in teams.items():
        t['journees'].sort(key=lambda j:j['journee'])
        if is_acbb(n):
            t['acbb']=True; t['calendar']={k:acbb_cal[k] for k in sorted(acbb_cal)}
        else:
            if '_acbbJ' in t: t['acbbJournee']=t['_acbbJ']; t['acbbDomext']=t.get('_acbbDom','')
        t.pop('_acbbJ',None); t.pop('_acbbDom',None)
        out.append(t)
    # ACBB en premier (cohérent avec l'original)
    out.sort(key=lambda t:0 if t.get('acbb') else 1)
    pool,level,lvc=META[key]
    return {'pool':pool,'level':level,'levelClass':lvc,'teams':out}

def build_standings(key, cx, d1, org):
    r=fb.get(f"xml_result_equ.php?cx_poule={cx}&D1={d1}&organisme_pere={org}&action=classement")
    rows=[]
    for c in re.findall(r'<classement>(.*?)</classement>', r, re.S):
        gf=int(re.sub(r'\D','',tg(c,'pg')) or 0); ga=int(re.sub(r'\D','',tg(c,'pp')) or 0)
        rows.append({'pos':int(tg(c,'clt') or 0),'name':tg(c,'equipe'),'pts':int(tg(c,'pts') or 0),
                     'mp':int(tg(c,'joue') or 0),'V':int(tg(c,'vic') or 0),'N':int(tg(c,'nul') or 0),
                     'D':int(tg(c,'def') or 0),'gf':gf,'ga':ga,'diff':gf-ga})
    # M3 : départage Art.14 régional (confrontation directe) -> ACBB devant Rambouillet à égalité de points
    if key=='M3':
        rows.sort(key=lambda x:x['pos'])
        if len(rows)>=2 and rows[0]['pts']==rows[1]['pts'] and is_acbb(rows[1]['name']):
            rows[0],rows[1]=rows[1],rows[0]; rows[0]['pos'],rows[1]['pos']=1,2
    return rows

def main():
    if not fb.APPID or not fb.MDP: import sys; sys.exit("FFTT_ID / FFTT_PWD manquants")
    # créneaux multiples : si déjà régénéré aujourd'hui, ne rien refaire (basé sur data/site.json)
    if os.environ.get('FFTT_SKIP_IF_FRESH')=='1':
        try:
            prev=json.load(open("data/site.json")).get('built','')[:10]
            if prev==datetime.datetime.now(datetime.timezone.utc).date().isoformat():
                print(f"site.json déjà à jour ({prev}) — skip."); return
        except Exception: pass
    eq=fb.get(f"xml_equipe.php?numclu={fb.CLUB}&type=A")
    coords={}   # key -> (cx,D1,org)
    for mm in re.finditer(r'<equipe>(.*?)</equipe>', eq, re.S):
        b=mm.group(1); lib=tg(b,'libequipe')
        if ' - Phase 2' not in lib: continue
        nm=fb.nrm(lib.replace(' - Phase 2',''))
        key=fb.TEAMKEY.get(nm)
        if not key or key not in META: continue
        m=re.search(r'<liendivision><!\[CDATA\[(.*?)\]\]>',b)
        p=dict(x.split('=') for x in html.unescape(m.group(1)).split('&'))
        coords[key]=(p['cx_poule'],p['D1'],p['organisme_pere'])
    DATA={}; STAND={}
    for key in ORDER:
        if key not in coords: print(f"  {key} : poule introuvable, ignorée"); continue
        cx,d1,org=coords[key]
        DATA[key]=build_pool(key,cx,d1,org); time.sleep(0.2)
        STAND[key]=build_standings(key,cx,d1,org); time.sleep(0.2)
        nj=sum(len(t['journees']) for t in DATA[key]['teams'])
        print(f"  {key} : {len(DATA[key]['teams'])} équipes, {nj} journées, {len(STAND[key])} au classement")
    out={'built':datetime.datetime.now(datetime.timezone.utc).isoformat(),'DATA':DATA,'STANDINGS':STAND}
    json.dump(out, open("data/site.json","w"), ensure_ascii=False)
    # site.js : chargé en <script> AVANT le script de page -> DATA/STANDINGS dispo en synchrone (pas de réécriture async)
    with open("data/site.js","w",encoding="utf-8") as f:
        f.write("window.__SITE="+json.dumps(out,ensure_ascii=False)+";")
    print(f"OK — data/site.json + data/site.js écrits ({len(DATA)} équipes).")

if __name__=='__main__': main()
