#!/usr/bin/env python3
"""Collecteur ACBB TT — génère un profil JSON par joueur depuis l'API FFTT (SmartPing).
Identifiants via variables d'environnement FFTT_ID / FFTT_PWD (jamais en dur).
Sortie : data/players/<licence>.json + data/players_index.json
Usage : python3 fftt_build.py [licence1 licence2 ...]   (sans arg = tout le club)
"""
import os, sys, json, re, html, time, hashlib, hmac, datetime, random, string, unicodedata
APPID=os.environ.get('FFTT_ID'); MDP=os.environ.get('FFTT_PWD'); CLUB="08920049"
BASE="http://www.fftt.com/mobile/pxml/"
serie=''.join(random.choices(string.ascii_uppercase+string.digits,k=15)); cle=hashlib.md5((MDP or '').encode()).hexdigest()
def auth():
    tm=datetime.datetime.now().strftime("%Y%m%d%H%M%S")+"000"
    return f"serie={serie}&tm={tm}&tmc={hmac.new(cle.encode(),tm.encode(),hashlib.sha1).hexdigest()}&id={APPID}"
def get(ep):
    for _ in range(4):
        try:
            import requests
            r=requests.get(BASE+ep+("&" if "?" in ep else "?")+auth(),timeout=25); r.encoding='ISO-8859-1'
            if r.status_code==200 and '<' in r.text: return r.text
        except Exception: pass
        time.sleep(0.5)
    return ''
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
MB=[(2025,9),(2025,10),(2025,11),(2025,12),(2026,1),(2026,2),(2026,3),(2026,4),(2026,5),(2026,6),(2026,7)]
EXACT = os.environ.get('FFTT_FAST','0') != '1'   # exact = reconstruire le mensuel adversaire (défaut). FFTT_FAST=1 -> hybride léger
OPPC={}   # cache adversaire: licence -> (initm, [(date,pointres)])
def opp_mensuel_at(lic, date):
    if not lic: return None
    if lic not in OPPC:
        lb=get(f"xml_licence_b.php?licence={lic}"); im=re.search(r'<initm>([-\d.]+)',lb)
        pm=get(f"xml_partie_mysql.php?licence={lic}")
        hh=[]
        for b in re.findall(r'<partie>(.*?)</partie>', pm, re.S):  # parsing par bloc (date AVANT pointres dans le record)
            d=tag(b,'date'); pr=tag(b,'pointres')
            if d and pr: hh.append((d,float(pr)))
        OPPC[lic]=(float(im.group(1)) if im else None, hh)
    im,hh=OPPC[lic]
    if im is None: return None
    cut=monthstart(date); return im+sum(pr for d,pr in hh if dn(d)<cut)

# nom d'équipe ACBB -> clé (M2..M17/F1..F3) pour les splits
TEAMKEY={nrm(k):v for k,v in {
 'BOULOGNE BILLANCOURT 1':'F1','BOULOGNE BILLANCOURT 2':'F2','BOULOGNE BILLAN 3':'F3',
 'BOULOGNE BILLANCOURT AC 2':'M2','BOULOGNE BILLANCOURT 3':'M3','BOULOGNE BILLANCOURT 4':'M4','BOULOGNE BILLANCOURT 5':'M5',
 'BOULOGNE BILLAN 6':'M6','BOULOGNE BILLAN 7':'M7','BOULOGNE BILLAN 8':'M8','BOULOGNE BILLAN 9':'M9','BOULOGNE BILLAN 10':'M10',
 'BOULOGNE BILLAN 11':'M11','BOULOGNE BILLAN 12':'M12','BOULOGNE BILLAN 13':'M13','BOULOGNE BILLAN 14':'M14',
 'BOULOGNE BILLAN 15':'M15','BOULOGNE BILLAN 16':'M16','BOULOGNE BILLAN 17':'M17'}.items()}
def build_team_detail(club=CLUB):
    """Parcourt toutes les rencontres ACBB (championnat phase 2) une fois, et renvoie
       par joueur ACBB : manches, doubles, set le plus serré, matchs en 5 manches, split par équipe."""
    eq=get(f"xml_equipe.php?numclu={club}&type=A")
    links=[(lib.split(' - ')[0].strip(), html.unescape(l))
           for lib,l in re.findall(r'<libequipe>(.*?)</libequipe>.*?<liendivision><!\[CDATA\[(.*?)\]\]>', eq, re.S) if 'Phase 2' in lib]
    ACBB=set()
    for (nm,pr) in roster(club).values(): ACBB.add(nrm(nm+pr))
    det={}
    def D(name):
        return det.setdefault(nrm(name), {'mw':0,'ml':0,'dw':0,'dt':0,'five':0,'fivew':0,'closest':None,'team':{}})
    for tname,link in links:
        tkey=TEAMKEY.get(nrm(tname), tname)
        res=get("xml_result_equ.php?"+link)
        for tb in re.finditer(r'<tour>(.*?)</tour>', res, re.S):
            blk=tb.group(1)
            ea,eb=tag(blk,'equa'),tag(blk,'equb')
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
def build_player(lic, nom, prenom, team_detail=None, allp=None):
    lb=get(f"xml_licence_b.php?licence={lic}")
    initm=float(tag(lb,'initm') or 0) or None
    point=tag(lb,'point'); pointm=tag(lb,'pointm'); apointm=tag(lb,'apointm')
    offpts = int(point) if (point and point.isdigit()) else None
    # niveau de référence quand l'API ne donne pas de mensuel (ex: licencié récent, pas d'historique) :
    # mensuel > début saison > officiel figé > 0. Évite un "my=0" qui fausse toutes les perfs.
    base_level = (float(pointm) if pointm else None)
    if base_level is None: base_level = initm if initm is not None else (float(offpts) if offpts is not None else 0)
    # historique points (validé) pour mensuel + jointure pointres par idpartie
    pmysql=get(f"xml_partie_mysql.php?licence={lic}")
    hist=[]; pts_by_id={}; advlic_by_id={}
    for b in re.findall(r'<partie>(.*?)</partie>', pmysql, re.S):
        d=tag(b,'date'); pr=tag(b,'pointres'); idp=tag(b,'idpartie'); al=tag(b,'advlic')
        if d and pr: hist.append((d,float(pr)))
        if idp and pr: pts_by_id[idp]=float(pr)
        if idp and al: advlic_by_id[idp]=al
    def mensuel_at(date):
        if initm is None: return None
        cut=monthstart(date); return initm+sum(pr for dd,pr in hist if dn(dd)<cut)
    # toutes les parties (validé + non validé) avec nom d'épreuve
    if allp is None: allp=get(f"xml_partie.php?numlic={lic}")
    comps={}; tot_pts=0.0; nonval_pts=0.0; perfs=0; cperfs=0; V=D=0; best=None; worst=None
    for b in re.findall(r'<partie>(.*?)</partie>', allp, re.S):
        date=tag(b,'date'); opp=tag(b,'nom'); ocls=tag(b,'classement'); epr=tag(b,'epreuve')
        won = tag(b,'victoire')=='V'; coef=float(tag(b,'coefchamp') or 1); idp=tag(b,'idpartie')
        if ' - ' in ocls: ocls=ocls.split(' - ')[-1]   # joueurs nationaux : "N95 - 2846" -> points = 2846
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
    if team_detail and 'equipe' in comps:
        d=team_detail.get(nrm(nom+prenom))
        if d:
            mtot=d['mw']+d['ml']
            comps['equipe']['detail']={
                'manches_w':d['mw'],'manches_t':mtot,'manches_pct':round(100*d['mw']/mtot) if mtot else 0,
                'doubles_w':d['dw'],'doubles_t':d['dt'],
                'five':d['five'],'five_w':d['fivew'],
                'closest':({'score':f"{d['closest'][0]+2}-{d['closest'][0]}",'opp':d['closest'][1]} if d['closest'] else None),
                'splits':[{'team':k,'w':v[0],'t':v[1]} for k,v in sorted(d['team'].items())],
            }
    # "à venir" retiré pour l'instant (pas calculable de façon fiable via l'API ; chantier ultérieur)
    avenir = None
    timeline=[]
    if initm is not None:
        for (lab,(yy,mm)) in list(zip(MOIS,MB))[:-1]:   # Sept..Juin (escalier mensuel)
            cut=yy*10000+mm*100+1
            timeline.append({'m':lab,'v':round(initm+sum(pr for dd,pr in hist if dn(dd)<cut),1)})
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
                      'debut':round(initm) if initm else None,'avenir':avenir},
        'timeline':timeline,
        'saison':{'V':V,'D':D,'parties':tot,'winpct':round(100*V/tot) if tot else 0,
                  'perfs':perfs,'contre_perfs':cperfs,'best':best,'worst':worst},
        'competitions':sorted([c for c in comps.values() if c['key']!='autre'], key=lambda c:-(c['V']+c['D'])),
    }
STATE_PATH='data/_state.json'; OPP_PATH='data/_oppcache.json'
def match_sig(allp):
    # signature des matchs d'un joueur (id + date + résultat) -> détecte un nouveau match sans tout recalculer
    items=sorted((tag(b,'idpartie') or '', tag(b,'date') or '', tag(b,'victoire') or '')
                 for b in re.findall(r'<partie>(.*?)</partie>', allp, re.S))
    return hashlib.sha1(repr(items).encode()).hexdigest()
def load_oppcache(month):
    try:
        oc=json.load(open(OPP_PATH))
        if oc.get('month')==month:
            for k,v in oc.get('data',{}).items(): OPPC[k]=(v[0],[tuple(x) for x in v[1]])
            return len(OPPC)
    except Exception: pass
    return 0
def save_oppcache(month):
    data={k:[im,[list(x) for x in hh]] for k,(im,hh) in OPPC.items()}
    json.dump({'month':month,'data':data}, open(OPP_PATH,'w'), ensure_ascii=False)

def main():
    if not APPID or not MDP: sys.exit("FFTT_ID / FFTT_PWD manquants (env vars)")
    args=sys.argv[1:]
    TOP=int(os.environ.get('FFTT_TOP','100') or 0)   # 0 = tout le club ; sinon les N mieux classés AYANT joué ≥1 match
    MONTH=os.environ.get('FFTT_MONTH') or datetime.date.today().strftime('%Y%m')
    FULL=os.environ.get('FFTT_FULL','0')=='1'         # 1 = tout reconstruire (ignore le cache)
    # état précédent : on ne réutilise que si même mois (les classements mensuels FFTT changent au 1er du mois)
    prev={}
    try:
        st=json.load(open(STATE_PATH))
        if not FULL and st.get('month')==MONTH: prev=st.get('sig',{})
    except Exception: pass
    nb_opp = load_oppcache(MONTH) if not FULL else 0
    mode = "COMPLET (FFTT_FULL)" if FULL else ("INCRÉMENTAL" if prev else f"COMPLET (1er run du mois {MONTH})")
    print(f"Mode : {mode} — cache adverse : {nb_opp} joueurs préchargés")
    if args:
        ros=roster(CLUB); candidates=[(l, *ros.get(l,('?','')), 0) for l in args]; need=len(candidates)
    else:
        candidates=ranked_roster(CLUB, 0)   # tout le club, trié par classement décroissant
        need = TOP if TOP>0 else len(candidates)
    print("Collecte du détail championnat (chp_renc)…")
    team_detail=build_team_detail(CLUB)
    print(f"  {len(team_detail)} joueurs ACBB avec détail championnat.")
    os.makedirs('data/players', exist_ok=True); index=[]; kept=0; skipped=0; rebuilt=0; reused=0; new_sig={}
    for (lic,nom,prenom,pts) in candidates:
        if kept>=need: break
        try:
            allp=get(f"xml_partie.php?numlic={lic}")   # appel léger : sert à la signature ET au build si besoin
            sig=match_sig(allp); new_sig[lic]=sig
            fpath=f"data/players/{lic}.json"
            unchanged = (not FULL) and (not args) and prev.get(lic)==sig and os.path.exists(fpath)
            if unchanged:
                prof=json.load(open(fpath)); reused+=1
            else:
                prof=build_player(lic,nom,prenom,team_detail,allp=allp); rebuilt+=1
                if not args and prof['saison']['parties']==0:   # exclure ceux qui n'ont pas joué (pros, inactifs)
                    skipped+=1; continue
                json.dump(prof, open(fpath,"w"), ensure_ascii=False)
            index.append({'lic':lic,'nom':nom,'prenom':prenom,
                          'mensuel':prof['classement']['mensuel'],'parties':prof['saison']['parties']})
            kept+=1
            flag='=' if unchanged else '↻'
            print(f"[{kept}/{need}] {flag} {lic} {nom} {prenom} — {prof['saison']['parties']}p {prof['saison']['V']}V/{prof['saison']['D']}D")
        except Exception as e:
            print(f"  {lic} ERREUR: {e}")
        time.sleep(0.15)
    json.dump(index, open("data/players_index.json","w"), ensure_ascii=False)
    if not args:   # on ne met à jour l'état/cache que sur un run complet du club
        json.dump({'month':MONTH,'sig':new_sig}, open(STATE_PATH,'w'), ensure_ascii=False)
        save_oppcache(MONTH)
    print(f"OK — {kept} profils ({reused} réutilisés, {rebuilt} reconstruits, {skipped} sans match ignorés).")
if __name__=='__main__': main()
