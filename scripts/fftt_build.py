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
MOIS=['Sept','Oct','Nov','Déc','Janv','Fév','Mars','Avr','Mai','Juin','Juil']
MB=[(2025,9),(2025,10),(2025,11),(2025,12),(2026,1),(2026,2),(2026,3),(2026,4),(2026,5),(2026,6),(2026,7)]
EXACT = os.environ.get('FFTT_FAST','0') != '1'   # exact = reconstruire le mensuel adversaire (défaut). FFTT_FAST=1 -> hybride léger
OPPC={}   # cache adversaire: licence -> (initm, [(date,pointres)])
def opp_mensuel_at(lic, date):
    if not lic: return None
    if lic not in OPPC:
        lb=get(f"xml_licence_b.php?licence={lic}"); im=re.search(r'<initm>([-\d.]+)',lb)
        pm=get(f"xml_partie_mysql.php?licence={lic}")
        OPPC[lic]=(float(im.group(1)) if im else None,
                   [(d,float(p)) for p,d in re.findall(r'<pointres>([-\d.]+)</pointres>.*?<date>(.*?)</date>',pm,re.S)])
    im,hh=OPPC[lic]
    if im is None: return None
    cut=monthstart(date); return im+sum(pr for d,pr in hh if dn(d)<cut)
def build_player(lic, nom, prenom):
    lb=get(f"xml_licence_b.php?licence={lic}")
    initm=float(tag(lb,'initm') or 0) or None
    point=tag(lb,'point'); pointm=tag(lb,'pointm')
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
    allp=get(f"xml_partie.php?numlic={lic}")
    comps={}; tot_pts=0.0; perfs=0; cperfs=0; V=D=0; best=None; worst=None
    for b in re.findall(r'<partie>(.*?)</partie>', allp, re.S):
        date=tag(b,'date'); opp=tag(b,'nom'); ocls=tag(b,'classement'); epr=tag(b,'epreuve')
        won = tag(b,'victoire')=='V'; coef=float(tag(b,'coefchamp') or 1); idp=tag(b,'idpartie')
        try: ocls=int(re.sub(r'\D','',ocls) or 0)
        except: ocls=0
        my=mensuel_at(date) or (initm or 0)
        # niveau adversaire : exact = mensuel au moment du match (via licence des matchs homologués) ; sinon classement courant
        olvl=None
        if EXACT: olvl=opp_mensuel_at(advlic_by_id.get(idp), date)
        if olvl is None: olvl=ocls
        olvl=round(olvl)
        pts = pts_by_id.get(idp); pts = pts if pts is not None else grille(my,olvl,won,coef)
        tot_pts+=pts
        key,label=categorize(epr)
        c=comps.setdefault(key,{'key':key,'label':label,'V':0,'D':0,'pg':0.0,'pl':0.0,'perf':0,'cperf':0,'matches':[]})
        if won: V+=1; c['V']+=1
        else: D+=1; c['D']+=1
        if pts>0: c['pg']+=pts
        else: c['pl']+=pts
        gap=round(olvl-my)  # >0 = adversaire mieux classé (au moment du match)
        if won and gap>0: perfs+=1; c['perf']+=1
        if (not won) and gap<0: cperfs+=1; c['cperf']+=1
        if won and (best is None or gap>best['delta']): best={'delta':gap,'opp':opp,'opp_cls':olvl,'my':round(my),'date':date,'comp':label}
        if (not won) and (worst is None or (-gap)>worst['delta']): worst={'delta':-gap,'opp':opp,'opp_cls':olvl,'my':round(my),'date':date,'comp':label}
        c['matches'].append({'date':date,'opp':opp,'opp_cls':olvl,'won':won,'pts':round(pts,2)})
    for c in comps.values():
        c['pg']=round(c['pg'],1); c['pl']=round(c['pl'],1); c['solde']=round(c['pg']+c['pl'],1)
        n=c['V']+c['D']; c['winpct']=round(100*c['V']/n) if n else 0
    avenir = round((initm or 0)+tot_pts) if initm is not None else None
    timeline=[]
    if initm is not None:
        for (lab,(yy,mm)) in zip(MOIS,MB):
            cut=yy*10000+mm*100+1
            timeline.append({'m':lab,'v':round(initm+sum(pr for dd,pr in hist if dn(dd)<cut),1)})
        if timeline: timeline[-1]={'m':'Juil','v':avenir,'avenir':True}
    tot=V+D
    return {
        'lic':lic,'nom':nom,'prenom':prenom,'club':CLUB,
        'classement':{'officiel':int(point) if point.isdigit() else point,
                      'mensuel':round(float(pointm)) if pointm else None,
                      'debut':round(initm) if initm else None,'avenir':avenir},
        'timeline':timeline,
        'saison':{'V':V,'D':D,'parties':tot,'winpct':round(100*V/tot) if tot else 0,
                  'perfs':perfs,'contre_perfs':cperfs,'best':best,'worst':worst},
        'competitions':sorted(comps.values(), key=lambda c:-(c['V']+c['D'])),
    }
def main():
    if not APPID or not MDP: sys.exit("FFTT_ID / FFTT_PWD manquants (env vars)")
    args=sys.argv[1:]
    ros=roster(CLUB)
    lics = args if args else list(ros.keys())
    os.makedirs('data/players', exist_ok=True); index=[]
    for i,lic in enumerate(lics):
        nom,prenom = ros.get(lic, ('?',''))
        try:
            prof=build_player(lic,nom,prenom)
            json.dump(prof, open(f"data/players/{lic}.json","w"), ensure_ascii=False)
            index.append({'lic':lic,'nom':nom,'prenom':prenom,
                          'mensuel':prof['classement']['mensuel'],'parties':prof['saison']['parties']})
            print(f"[{i+1}/{len(lics)}] {lic} {nom} {prenom} — {prof['saison']['parties']}p {prof['saison']['V']}V/{prof['saison']['D']}D, {len(prof['competitions'])} compét.")
        except Exception as e:
            print(f"[{i+1}/{len(lics)}] {lic} ERREUR: {e}")
        time.sleep(0.2)
    json.dump(index, open("data/players_index.json","w"), ensure_ascii=False)
    print(f"OK — {len(index)} profils générés.")
if __name__=='__main__': main()
