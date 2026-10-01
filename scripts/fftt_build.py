#!/usr/bin/env python3
"""Collecteur ACBB TT — génère un profil JSON par joueur depuis l'API FFTT (SmartPing).
Identifiants via variables d'environnement FFTT_ID / FFTT_PWD (jamais en dur).
Sortie : data/players/<licence>.json + data/players_index.json
Usage : python3 fftt_build.py [licence1 licence2 ...]   (sans arg = tout le club)
"""
import os, sys, json, re, html, time, hashlib, hmac, datetime, random, string, unicodedata
from fftt_quality import profile_signature, require_xml, acbb_team_key
APPID=os.environ.get('FFTT_ID'); MDP=os.environ.get('FFTT_PWD'); CLUB="08920049"
# Joueurs partis du club à exclure du roster (annuaire + scoring), même si la FFTT les liste encore.
EXCLUDE_LIC = {'9236792', '7871729'}   # partis du club : Douss, Mondino (14/09/2026)  # Mehdi DOUSS (départ 08/2026) — German RODRIGUEZ réintégré le 03/09 (pool D2)
BASE="https://www.fftt.com/mobile/pxml/"
serie=''.join(random.choices(string.ascii_uppercase+string.digits,k=15)); cle=hashlib.md5((MDP or '').encode()).hexdigest()
def auth():
    tm=datetime.datetime.now().strftime("%Y%m%d%H%M%S")+"000"
    return f"serie={serie}&tm={tm}&tmc={hmac.new(cle.encode(),tm.encode(),hashlib.sha1).hexdigest()}&id={APPID}"
def get(ep):
    for _ in range(4):
        try:
            import requests
            r=requests.get(BASE+ep+("&" if "?" in ep else "?")+auth(),timeout=25); r.encoding='ISO-8859-1'
            if r.status_code==200: return require_xml(r.text)
        except Exception: pass
        time.sleep(0.5)
    raise RuntimeError('FFTT indisponible : '+ep.split('?')[0])
def tag(s,t):
    m=re.search('<'+t+'>(.*?)</'+t+'>',s,re.S); return m.group(1).strip() if m else ''
def nrm(s):
    s=unicodedata.normalize('NFKD',(s or '')); return re.sub(r'[^A-Za-z0-9]','',''.join(c for c in s if not unicodedata.combining(c))).upper()
def dn(x):
    try: d,m,y=x.split('/'); return int(y)*10000+int(m)*100+int(d)
    except: return 0
def monthstart(x):
    try: d,m,y=x.split('/'); return int(y)*10000+int(m)*100+1
    except: return 0
# ---- grille officielle FFTT (coef 1) ----
GR=[(24,6,-5,6,-5),(49,5.5,-4.5,7,-6),(99,5,-4,8,-7),(149,4,-3,10,-8),(199,3,-2,13,-10),
    (299,2,-1,17,-12.5),(399,1,-0.5,22,-16),(499,0.5,0,28,-20),(10**9,0,0,40,-29)]
def grille(my,opp,won,coef):
    # hi_ = je suis mieux classé. Défaite : si je suis mieux classé = contre (pa, lourd), sinon normale (pn)
    gap=abs(my-opp); hi_=my>=opp
    for h,gn,pn,ga,pa in GR:
        if gap<=h:
            if won: return round((gn if hi_ else ga)*coef,2)
            return round((pa if hi_ else pn)*coef,2)
    return 0
# ---- catégorisation par nom d'épreuve ----
def categorize(epr):
    e=epr.lower()
    # séparation M/F du championnat par équipes (demande sportive 16/07/2026).
    # ⚠️ à vérifier à la reprise : libellé exact de l'épreuve féminine dans xml_partie
    if 'quipe' in e and ('fem' in e or 'dame' in e):
        return ('equipe_f','Championnat par équipe · Féminin')
    if 'quipe' in e: return ('equipe','Championnat par équipe')
    if 'crit' in e: return ('criterium','Critérium fédéral')
    if 'championnat de paris' in e or 'paris idf' in e: return ('paris','Championnat de Paris')
    if 'tournoi' in e: return ('tournoi','Tournois')
    if 'coupe' in e: return ('coupe','Coupe par équipes')
    return ('autre','Autres')
def roster(club):
    out={}
    for endp in ['xml_liste_joueur.php','xml_liste_joueur_o.php']:
        for m in re.finditer(r'<licence>(\d+)</licence>.*?<nom>(.*?)</nom>.*?<prenom>(.*?)</prenom>', get(f"{endp}?club={club}"), re.S):
            out.setdefault(m.group(1), (m.group(2).strip(), m.group(3).strip()))
    return out
def ranked_roster(club, n):
    # trie par classement (points) via xml_liste_joueur_o, renvoie les n meilleurs : [(lic,nom,prenom,points)]
    pl={}
    for blk in re.findall(r'<joueur>(.*?)</joueur>', get(f"xml_liste_joueur_o.php?club={club}"), re.S):
        lic=tag(blk,'licence')
        if not lic: continue
        try: pts=int(re.sub(r'\D','', tag(blk,'points')) or 0)
        except: pts=0
        nom=tag(blk,'nom'); prenom=tag(blk,'prenom')
        if lic not in pl or pts>pl[lic][2]: pl[lic]=(nom,prenom,pts)
    ranked=sorted(pl.items(), key=lambda kv:-kv[1][2])
    if n and n>0: ranked=ranked[:n]
    return [(lic,v[0],v[1],v[2]) for lic,v in ranked]
MOIS=['Sept','Oct','Nov','Déc','Janv','Fév','Mars','Avr','Mai','Juin','Juil']
SAISON='2026/2027'
SEASON_START=20260701   # AAAAMMJJ : seules les parties à partir de cette date comptent pour le récap et le mensuel de la saison   # saison courante : fenêtre du récap et du calendrier mensuel (bascule 16/09/2026 ; récap 25/26 archivé dans data/archive/2025-2026/players)
MB=[(2026,9),(2026,10),(2026,11),(2026,12),(2027,1),(2027,2),(2027,3),(2027,4),(2027,5),(2027,6),(2027,7)]
EXACT = os.environ.get('FFTT_FAST','0') != '1'   # exact = reconstruire le mensuel adversaire (défaut). FFTT_FAST=1 -> hybride léger
OPPC_AT=time.time()
OPPC={}   # cache adversaire: licence -> (initm, [(date,pointres)])
PAIR2TEAM={}  # (nrm joueur ACBB)|(nrm adversaire) -> clé d'équipe (M2..F3), pour rattacher chaque match simple à son équipe
def opp_mensuel_at(lic, date):
    if not lic: return None
    if lic not in OPPC:
        lb=get(f"xml_licence_b.php?licence={lic}"); im=re.search(r'<initm>([-\d.]+)',lb)
        po=tag(lb,'point'); base=(float(po) if po and po.replace('.','',1).isdigit() else (float(im.group(1)) if im else None))
        pm=get(f"xml_partie_mysql.php?licence={lic}")
        hh=[]
        for b in re.findall(r'<partie>(.*?)</partie>', pm, re.S):  # parsing par bloc (date AVANT pointres dans le record)
            d=tag(b,'date'); pr=tag(b,'pointres')
            if d and pr and dn(d)>=SEASON_START: hh.append((d,float(pr)))   # saison courante uniquement (base = officiel de la saison)
        OPPC[lic]=(base, hh)
    im,hh=OPPC[lic]
    if im is None: return None
    cut=monthstart(date); return im+sum(pr for d,pr in hh if dn(d)<cut)

def build_team_detail(club=CLUB):
    """Parcourt toutes les rencontres ACBB (championnat de la saison) une fois, et renvoie
       par joueur ACBB : manches, doubles, set le plus serré, matchs en 5 manches, split par équipe."""
    eq=get(f"xml_equipe.php?numclu={club}&type=A")
    links=[]
    for block in re.findall(r'<equipe>(.*?)</equipe>',eq,re.S):
        label=tag(block,'libequipe')
        if 'Phase' not in label: continue
        link=re.search(r'<liendivision><!\[CDATA\[(.*?)\]\]>',block,re.S)
        if not link: continue
        tkey=acbb_team_key(label,tag(block,'libdivision'))
        if not tkey: raise RuntimeError('Équipe FFTT sans championnat identifiable')
        links.append((tkey,html.unescape(link.group(1))))
    ACBB=set()
    for (nm,pr) in roster(club).values(): ACBB.add(nrm(nm+pr))
    det={}
    def D(name):
        return det.setdefault(nrm(name), {}).setdefault(tkey[0], {'mw':0,'ml':0,'dw':0,'dt':0,'five':0,'fivew':0,'closest':None,'team':{}})
    for tkey,link in links:
        res=get("xml_result_equ.php?"+link)
        for tb in re.finditer(r'<tour>(.*?)</tour>', res, re.S):
            blk=tb.group(1)
            ea,eb=tag(blk,'equa'),tag(blk,'equb')
            date=(tag(blk,'datereelle') or tag(blk,'dateprevue'))[:10]
            if re.match(r'^\d{4}-\d\d-\d\d$',date): date=date[8:10]+'/'+date[5:7]+'/'+date[:4]
            if not (nrm(ea).startswith('BOULOGNEBILLAN') or nrm(eb).startswith('BOULOGNEBILLAN')): continue
            lm=re.search(r'<lien><!\[CDATA\[(.*?)\]\]>',blk,re.S)
            if not lm: continue
            cr=get("xml_chp_renc.php?"+html.unescape(lm.group(1)))
            for pm in re.finditer(r'<partie>(.*?)</partie>', cr, re.S):
                b=pm.group(1); ja,jb=tag(b,'ja'),tag(b,'jb'); sa,sb=tag(b,'scorea'),tag(b,'scoreb'); detail=tag(b,'detail')
                if ' et ' in (ja+jb):                         # double : côté ACBB par appartenance roster
                    pa=[x.strip() for x in re.split(r'\s+et\s+', ja)]; pb=[x.strip() for x in re.split(r'\s+et\s+', jb)]
                    if any(nrm(x) in ACBB for x in pa): pair, mes,ops, a_is = pa, sa,sb, True
                    elif any(nrm(x) in ACBB for x in pb): pair, mes,ops, a_is = pb, sb,sa, False
                    else: continue
                    won = mes not in ('','-') and (ops in ('','-') or float(mes)>float(ops))
                    for nm in pair:
                        d=D(nm); d['dt']+=1; d['dw']+= 1 if won else 0
                    continue
                # simple : qui est ACBB (ja ou jb) via le roster
                if nrm(ja) in ACBB: acbb_ja=True; me=ja
                elif nrm(jb) in ACBB: acbb_ja=False; me=jb
                else: continue
                opp_name = (jb if acbb_ja else ja).strip()
                if opp_name: PAIR2TEAM[(nrm(me),nrm(opp_name),date,tkey[0])] = tkey   # rattache (joueur ACBB, adversaire) -> équipe
                sets=[int(t) for t in detail.split() if re.match(r'^-?\d+$',t)]
                ws=sum(1 for v in sets if (v>0)==acbb_ja); ls=len(sets)-ws   # manches (signe detail = côté A)
                won = (ws>ls) if sets else ((sa if acbb_ja else sb) not in ('','-'))
                d=D(me); d['mw']+=ws; d['ml']+=ls
                tk=d['team'].setdefault(tkey,[0,0]); tk[1]+=1; tk[0]+= 1 if won else 0
                if len(sets)==5: d['five']+=1; d['fivew']+= 1 if won else 0
                for v in sets:   # set le plus serré gagné
                    iwon=(v>0)==acbb_ja; lp=abs(v)
                    if iwon and lp>=8 and (d['closest'] is None or lp>d['closest'][0]):
                        d['closest']=(lp, (jb if acbb_ja else ja).strip())
    return det
def build_player(lic, nom, prenom, team_detail=None, allp=None, lb=None, pmysql=None):
    if lb is None: lb=get(f"xml_licence_b.php?licence={lic}")
    initm=float(tag(lb,'initm') or 0) or None
    point=tag(lb,'point'); pointm=tag(lb,'pointm'); apointm=tag(lb,'apointm')
    offpts = int(point) if (point and point.isdigit()) else None
    # niveau de référence quand l'API ne donne pas de mensuel (ex: licencié récent, pas d'historique) :
    # mensuel > début saison > officiel figé > 0. Évite un "my=0" qui fausse toutes les perfs.
    base_level = (float(pointm) if pointm else None)
    if base_level is None: base_level = initm if initm is not None else (float(offpts) if offpts is not None else 0)
    # historique points (validé) pour mensuel + jointure pointres par idpartie
    if pmysql is None: pmysql=get(f"xml_partie_mysql.php?licence={lic}")
    hist=[]; pts_by_id={}; advlic_by_id={}
    for b in re.findall(r'<partie>(.*?)</partie>', pmysql, re.S):
        d=tag(b,'date'); pr=tag(b,'pointres'); idp=tag(b,'idpartie'); al=tag(b,'advlic')
        if d and dn(d)<SEASON_START: continue          # parties des saisons précédentes : hors récap
        if d and pr: hist.append((d,float(pr)))
        if idp and pr: pts_by_id[idp]=float(pr)
        if idp and al: advlic_by_id[idp]=al
    # base de la saison = classement officiel 26/27 (l'initm de l'API reste celui de la saison passée tant que le
    # mensuel n'a pas basculé) ; repli initm puis niveau de référence.
    base26 = float(offpts) if offpts is not None else (initm if initm is not None else base_level)
    def mensuel_at(date):
        if base26 is None: return None
        cut=monthstart(date); return base26+sum(pr for dd,pr in hist if dn(dd)<cut)
    # toutes les parties (validé + non validé) avec nom d'épreuve
    if allp is None: allp=get(f"xml_partie.php?numlic={lic}")
    comps={}; tot_pts=0.0; nonval_pts=0.0; perfs=0; cperfs=0; V=D=0; best=None; worst=None
    team_levels=[]   # par match simple de championnat : {t:équipe, my:mensuel ACBB, opp:mensuel adverse}
    for b in re.findall(r'<partie>(.*?)</partie>', allp, re.S):
        date=tag(b,'date'); opp=tag(b,'nom'); ocls=tag(b,'classement'); epr=tag(b,'epreuve')
        if date and dn(date)<SEASON_START: continue      # sécurité : uniquement la saison courante
        won = tag(b,'victoire')=='V'; coef=float(tag(b,'coefchamp') or 1); idp=tag(b,'idpartie')
        # joueurs numérotés : "N95 - 2846" ou "N°254- M 2480pts" -> on veut les POINTS (2846 / 2480),
        # jamais le n° national. On lit « …pts » en priorité, sinon la partie après le tiret.
        mpts=re.search(r'(\d+)\s*pts', ocls, re.I)
        if mpts: ocls=mpts.group(1)
        elif ' - ' in ocls: ocls=ocls.split(' - ')[-1]
        try: ocls=int(re.sub(r'\D','',ocls) or 0)
        except: ocls=0
        my=mensuel_at(date) or base_level
        # niveau adversaire : exact = mensuel au moment du match (via licence des matchs homologués) ; sinon classement courant
        olvl=None
        if EXACT: olvl=opp_mensuel_at(advlic_by_id.get(idp), date)
        if olvl is None: olvl=ocls
        olvl=round(olvl)
        homol = idp in pts_by_id
        pts = pts_by_id[idp] if homol else grille(my,olvl,won,coef)
        tot_pts+=pts
        if not homol: nonval_pts+=pts   # points des matchs pas encore homologués (pour le "à venir")
        key,label=categorize(epr)
        if key in ('equipe','equipe_f') and ' et ' not in opp:   # match simple de championnat -> niveau par équipe
            # Date et championnat évitent de confondre deux rencontres de la même paire.
            tk = PAIR2TEAM.get((nrm(nom+prenom),nrm(opp),date,'F' if key=='equipe_f' else 'M'))
            if tk: team_levels.append({'t':tk,'my':round(my),'opp':olvl})
        c=comps.setdefault(key,{'key':key,'label':label,'V':0,'D':0,'pg':0.0,'pl':0.0,'perf':0,'cperf':0,'best':None,'worst':None,'matches':[]})
        if won: V+=1; c['V']+=1
        else: D+=1; c['D']+=1
        if pts>0: c['pg']+=pts
        else: c['pl']+=pts
        gap=round(olvl-my)  # >0 = adversaire mieux classé (au moment du match)
        rec={'delta':gap,'opp':opp,'opp_cls':olvl,'my':round(my),'date':date,'comp':label}
        if won and gap>0: perfs+=1; c['perf']+=1
        if (not won) and gap<0: cperfs+=1; c['cperf']+=1
        if won and (best is None or gap>best['delta']): best=rec
        if (not won) and (worst is None or (-gap)>worst['delta']): worst={**rec,'delta':-gap}
        # best/worst par compétition (en écart de classement, cohérent avec la saison)
        if won and (c['best'] is None or gap>c['best']['delta']): c['best']=rec
        if (not won) and (c['worst'] is None or (-gap)>c['worst']['delta']): c['worst']={**rec,'delta':-gap}
        c['matches'].append({'date':date,'opp':opp,'opp_cls':olvl,'won':won,'pts':round(pts,2)})
    for c in comps.values():
        c['pg']=round(c['pg'],1); c['pl']=round(c['pl'],1); c['solde']=round(c['pg']+c['pl'],1)
        n=c['V']+c['D']; c['winpct']=round(100*c['V']/n) if n else 0
    # détail championnat (manches/doubles/sets/splits) si dispo
    for genre,competition in [('M','equipe'),('F','equipe_f')]:
        d=(team_detail.get(nrm(nom+prenom)) or {}).get(genre) if team_detail else None
        if d and competition in comps:
            mtot=d['mw']+d['ml']
            comps[competition]['detail']={
                'manches_w':d['mw'],'manches_t':mtot,'manches_pct':round(100*d['mw']/mtot) if mtot else 0,
                'doubles_w':d['dw'],'doubles_t':d['dt'],
                'five':d['five'],'five_w':d['fivew'],
                'closest':({'score':f"{d['closest'][0]+2}-{d['closest'][0]}",'opp':d['closest'][1]} if d['closest'] else None),
                'splits':[{'team':k,'w':v[0],'t':v[1]} for k,v in sorted(d['team'].items())],
            }
    # "à venir" retiré pour l'instant (pas calculable de façon fiable via l'API ; chantier ultérieur)
    avenir = None
    timeline=[]
    if base26 is not None:
        for (lab,(yy,mm)) in list(zip(MOIS,MB))[:-1]:   # Sept..Juin (escalier mensuel depuis l'officiel de la saison)
            cut=yy*10000+mm*100+1
            timeline.append({'m':lab,'v':round(base26+sum(pr for dd,pr in hist if dn(dd)<cut),1)})
        # dernier point = mensuel officiel actuel (exact), pas de projection
        if pointm: timeline.append({'m':'Actuel','v':round(float(pointm)),'off':True})
    elif base_level:
        # pas d'historique mensuel : au moins un point "Actuel" pour ne pas avoir une courbe vide
        timeline.append({'m':'Actuel','v':round(base_level),'off':True})
    tot=V+D
    return {
        'lic':lic,'nom':nom,'prenom':prenom,'club':CLUB,
        'classement':{'officiel':int(point) if point.isdigit() else point,
                      'mensuel':round(float(pointm)) if pointm else (offpts if offpts is not None else None),
                      'debut':round(base26) if base26 is not None else None,'avenir':avenir},
        'timeline':timeline,
        'saison':{'V':V,'D':D,'parties':tot,'winpct':round(100*V/tot) if tot else 0,
                  'perfs':perfs,'contre_perfs':cperfs,
                  # solde = points nets gagnés/perdus en match depuis le début de saison (homologués au réel,
                  # estimés sinon) ; sert la carte « Plus fortes progressions » tant que le mensuel FFTT n'a pas basculé.
                  'solde':round(sum(c['pg']+c['pl'] for c in comps.values() if c['key']!='autre'),1),
                  'best':best,'worst':worst},
        'competitions':sorted([c for c in comps.values() if c['key']!='autre'], key=lambda c:-(c['V']+c['D'])),
        'team_levels':team_levels,
    }
STATE_PATH='data/_state.json'; OPP_PATH='data/_oppcache.json'

def team_info():
    pools=json.load(open('data/poules2627.json'))['poules']
    site=json.load(open('data/site.json'))
    result=[]
    for pool in pools:
        k=pool['acbb']; label=pool['division']
        standings=site.get('STANDINGS',{}).get(k,[])
        names={nrm(x.get('name')) for x in site.get('DATA',{}).get(k,{}).get('teams',[]) if x.get('acbb')}
        own=next((r for r in standings if nrm(r.get('name')) in names),None)
        pos=str(own.get('pos'))+'/'+str(len(standings)) if own and own.get('pos') and any(r.get('mp',0) for r in standings) else None
        result.append((k,label,label,k[0],pos))
    return result

def build_teams_json(profiles):
    """Agrège, par équipe puis par division, le mensuel réel ACBB vs adverse au moment des matchs."""
    acc={}   # tkey -> {'acbb':[...], 'opp':[...]}
    for p in profiles:
        for tl in (p.get('team_levels') or []):
            a=acc.setdefault(tl['t'], {'acbb':[],'opp':[]})
            if isinstance(tl.get('my'),(int,float)) and tl['my']>0: a['acbb'].append(tl['my'])
            if isinstance(tl.get('opp'),(int,float)) and tl['opp']>0: a['opp'].append(tl['opp'])
    avg=lambda l: round(sum(l)/len(l)) if l else None
    teams=[]; divacc={}
    for (k,short,label,genre,pos) in team_info():
        a=acc.get(k,{'acbb':[],'opp':[]})
        teams.append({'key':k,'short':short,'label':label,'genre':genre,'pos':pos,
                      'acbb':avg(a['acbb']),'opp':avg(a['opp']),'n':len(a['acbb'])})
        dk=(genre,label,short)
        d=divacc.setdefault(dk,{'acbb':[],'opp':[]})
        d['acbb']+=a['acbb']; d['opp']+=a['opp']
    divisions=[{'short':s,'label':lab,'genre':g,'acbb':avg(v['acbb']),'opp':avg(v['opp']),'n':len(v['acbb'])}
               for (g,lab,s),v in divacc.items()]
    return {'teams':teams,'divisions':divisions}
def match_sig(allp, licence='', validated='', details=None):
    return profile_signature(allp, licence, validated, details)
def load_oppcache(full=False):
    global OPPC_AT
    OPPC_AT=time.time()
    OPPC.clear()
    if full: return 0
    try:
        oc=json.load(open(OPP_PATH))
        if oc.get('season')!=SAISON: return 0
        age=time.time()-oc.get('at',0)
        if age<0 or age>24*3600: return 0
        OPPC_AT=oc['at']
        for k,v in oc.get('data',{}).items(): OPPC[k]=(v[0],[tuple(x) for x in v[1]])
        return len(OPPC)
    except (OSError,ValueError,TypeError): return 0
def save_oppcache():
    data={k:[im,[list(x) for x in hh]] for k,(im,hh) in OPPC.items()}
    json.dump({'at':OPPC_AT,'season':SAISON,'data':data}, open(OPP_PATH,'w'), ensure_ascii=False)

def main():
    if not APPID or not MDP: sys.exit("FFTT_ID / FFTT_PWD manquants (env vars)")
    args=sys.argv[1:]
    TOP=int(os.environ.get('FFTT_TOP','100') or 0)   # 0 = tout le club ; sinon les N mieux classés AYANT joué ≥1 match
    FULL=os.environ.get('FFTT_FULL','0')=='1'         # 1 = tout reconstruire (ignore le cache)
    # Créneaux multiples (runs programmés) : si déjà mis à jour aujourd'hui, on ne refait rien (0 appel API).
    # Un déclenchement manuel force toujours la mise à jour (FFTT_SKIP_IF_FRESH=0).
    if not args and not FULL and os.environ.get('FFTT_SKIP_IF_FRESH')=='1':
        try:
            built=json.load(open("data/meta.json")).get('built','')[:10]
            today_utc=datetime.datetime.now(datetime.timezone.utc).date().isoformat()
            if built==today_utc:
                print(f"Déjà à jour aujourd'hui ({built}) — run ignoré."); return
        except Exception: pass
    # Classement, homologation et détail de rencontre entrent dans la signature.
    prev={}
    try:
        st=json.load(open(STATE_PATH))
        if not FULL and st.get('season')==SAISON: prev=st.get('sig',{})
    except Exception: pass
    nb_opp = load_oppcache(FULL)
    mode = "COMPLET (FFTT_FULL)" if FULL else ("INCRÉMENTAL" if prev else "COMPLET (amorçage, pas de cache)")
    print(f"Mode : {mode} — cache adverse : {nb_opp} joueurs préchargés")
    if args:
        ros=roster(CLUB); candidates=[(l, *ros.get(l,('?','')), 0) for l in args]; need=len(candidates)
    else:
        candidates=ranked_roster(CLUB, 0)   # tout le club, trié par classement décroissant
        need = TOP if TOP>0 else len(candidates)
    print("Collecte du détail championnat (chp_renc)…")
    team_detail=build_team_detail(CLUB)
    print(f"  {len(team_detail)} joueurs ACBB avec détail championnat.")
    os.makedirs('data/players', exist_ok=True); index=[]; profiles=[]; kept=0; skipped=0; rebuilt=0; reused=0; new_sig={}; failed=0
    for (lic,nom,prenom,pts) in candidates:
        if kept>=need: break
        try:
            allp=get(f"xml_partie.php?numlic={lic}")   # appel léger : sert à la signature ET au build si besoin
            lb=get(f"xml_licence_b.php?licence={lic}")
            pmysql=get(f"xml_partie_mysql.php?licence={lic}")
            sig=match_sig(allp,lb,pmysql,{'detail':team_detail.get(nrm(nom+prenom)), 'opponent_cache_epoch':int(OPPC_AT)}); new_sig[lic]=sig
            fpath=f"data/players/{lic}.json"
            unchanged = (not FULL) and (not args) and prev.get(lic)==sig and os.path.exists(fpath)
            if unchanged:
                prof=json.load(open(fpath)); reused+=1
            else:
                prof=build_player(lic,nom,prenom,team_detail,allp=allp,lb=lb,pmysql=pmysql); rebuilt+=1
                # 26/27 : on garde TOUS les licenciés, même sans match (la fiche affiche alors le classement officiel
                # et « reviens après tes premiers matchs ») — indispensable pour la recherche joueur du nouveau site.
                json.dump(prof, open(fpath,"w"), ensure_ascii=False)
            index.append({'lic':lic,'nom':nom,'prenom':prenom,
                          'mensuel':prof['classement']['mensuel'],'parties':prof['saison']['parties'],
                          'officiel':prof['classement']['officiel'],'debut':prof['classement']['debut'],
                          'solde':prof['saison'].get('solde',0),
                          'V':prof['saison']['V'],'D':prof['saison']['D']})
            profiles.append(prof); kept+=1
            flag='=' if unchanged else '↻'
            print(f"[{kept}/{need}] {flag} {lic} {nom} {prenom} — {prof['saison']['parties']}p {prof['saison']['V']}V/{prof['saison']['D']}D")
        except Exception as e:
            failed+=1
            print("Profil non collecté : publication du lot annulée")
        time.sleep(0.15)
    if failed: sys.exit(f"ABORT: {failed} profil(s) incomplet(s), aucune publication.")
    # garde-fou : si l'API a flanché (collecte très incomplète), on n'écrase RIEN —
    # le run échoue, les données en prod restent intactes.
    if not args:
        try: prev_n=len(json.load(open("data/players_index.json")))
        except Exception: prev_n=0
        if prev_n>=20 and kept < prev_n*0.8:
            sys.exit(f"ABORT: collecte incomplète ({kept} profils vs {prev_n} précédents) — aucune écriture, run en échec.")
    if args:
        prior=json.load(open('data/players_index.json'))
        changed={p['lic'] for p in index}
        index=[p for p in prior if p['lic'] not in changed]+index
    index=[p for p in index if p.get('lic') not in EXCLUDE_LIC]   # retire les partis du club
    json.dump(index, open("data/players_index.json","w"), ensure_ascii=False)
    if not args:   # on ne met à jour l'état/cache/teams que sur un run complet du club
        tj=build_teams_json(profiles)
        json.dump(tj, open("data/teams.json","w"), ensure_ascii=False)
        n2=next((t for t in tj['teams'] if t['key']=='M2'), {})
        print("  teams.json : statistiques recalculées")
        # horodatage de la dernière mise à jour (UTC ISO) -> affiché formaté côté client (heure de Paris)
        json.dump({'built':datetime.datetime.now(datetime.timezone.utc).isoformat()}, open("data/meta.json","w"), ensure_ascii=False)
        json.dump({'built':datetime.date.today().isoformat(),'season':SAISON,'sig':new_sig}, open(STATE_PATH,'w'), ensure_ascii=False)
        save_oppcache()
    print(f"OK — {kept} profils ({reused} réutilisés, {rebuilt} reconstruits, {skipped} sans match ignorés).")
if __name__=='__main__': main()
