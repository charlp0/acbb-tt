#!/usr/bin/env python3
"""Archive FFTT — sauvegarde compos + classements de toutes les poules des divisions
où l'ACBB est engagée (92 + IDF, hors national), pour les 2 phases.
Identifiants via FFTT_ID / FFTT_PWD (jamais en dur).
Usage : FFTT_ID=.. FFTT_PWD=.. python3 scripts/fftt_archive.py <phase 1|2> <org 116|16|all>
Sortie : data/archive/2025-2026/phase-<p>/<division>/poule-<n>.json
"""
import os, sys, re, html, json, time, importlib.util
spec=importlib.util.spec_from_file_location("fb","scripts/fftt_build.py")
fb=importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
def tg(s,t):
    m=re.search('<'+t+'>(.*?)</'+t+'>',s,re.S); return m.group(1).strip() if m else ''
def pts(x):  # "M 726pts" -> 726 ; "" / "NC" -> None
    m=re.search(r'(\d+)', x or ''); return int(m.group(1)) if m else None
def divname(ld):  # "D92_D2 Messieurs_Ph2 Poule 4" -> "D92_D2 Messieurs"
    s=re.sub(r'\s*[Pp]oule\s*\d+.*$','',ld or '')
    s=re.sub(r'[_ ]*[Pp]h(ase)?\s*\d+\s*$','',s).strip(' _')
    return s
def slug(s):
    s=fb.nrm(divname(s)); return s[:40]

def lineups(renc_lien):
    """compo des 2 équipes (nom + points) depuis la feuille de rencontre."""
    r=fb.get("xml_chp_renc.php?"+renc_lien)
    A=[]; B=[]
    for j in re.findall(r'<joueur>(.*?)</joueur>', r, re.S):
        na,ca,nb,cb=tg(j,'xja'),tg(j,'xca'),tg(j,'xjb'),tg(j,'xcb')
        if na: A.append({'nom':na,'pts':pts(ca)})
        if nb: B.append({'nom':nb,'pts':pts(cb)})
    return A,B

def classement(d1,org,cx):
    r=fb.get(f"xml_result_equ.php?cx_poule={cx}&D1={d1}&organisme_pere={org}&action=classement")
    out=[]
    for c in re.findall(r'<classement>(.*?)</classement>', r, re.S):
        out.append({'clt':tg(c,'clt'),'equipe':tg(c,'equipe'),'pts':tg(c,'pts'),
                    'joue':tg(c,'joue'),'vic':tg(c,'vic'),'nul':tg(c,'nul'),'def':tg(c,'def'),
                    'pg':tg(c,'pg'),'pp':tg(c,'pp')})
    return out

def archive_poule(div, d1, org, cx, num, phase):
    cal=fb.get(f"xml_result_equ.php?cx_poule={cx}&D1={d1}&organisme_pere={org}")
    tours=re.findall(r'<tour>(.*?)</tour>', cal, re.S)
    rencs=[]
    for t in tours:
        ea,eb=tg(t,'equa'),tg(t,'equb')
        if not(ea and eb): continue   # exempt
        lm=re.search(r'<lien><!\[CDATA\[(.*?)\]\]>', t)
        la,lb=([],[])
        if lm: la,lb=lineups(html.unescape(lm.group(1))); time.sleep(0.2)
        rencs.append({'date':tg(t,'datereelle') or tg(t,'dateprevue'),
                      'equa':ea,'equb':eb,'scorea':tg(t,'scorea'),'scoreb':tg(t,'scoreb'),
                      'compo_a':la,'compo_b':lb})
    if not rencs: return None
    clt=classement(d1,org,cx); time.sleep(0.2)
    return {'division':div,'organisme':org,'phase':phase,'poule':num,'cx_poule':cx,
            'classement':clt,'rencontres':rencs}

def scan(phase, cx_start, cx_end, d1s):
    """Rattrapage : archive toute poule 2025/26 qui répond encore par cx_poule direct.
    D1 (ID de division) est requis par l'API et quasi-séquentiel par niveau
    (découverte juin 2026 : R2 M=199051, R3 M=199052 -> R1 M≈199050, PN M≈199049).
    Chaque cx est testé avec chaque D1 candidat. Dossier L08SCAN, tri manuel ensuite.
    Usage : fftt_archive.py scan <phase 1|2> <cx_start> <cx_end> <D1[,D1...]>"""
    # Sonde : une poule déjà archivée doit répondre avec son propre D1 (R2 M=199051)
    probe_cx={'1':1141541,'2':1142533}[str(phase)]
    old=archive_poule('probe','199051','16',probe_cx,None,phase)
    print(f"Sonde (cx {probe_cx}, D1=199051) : "+(f"OK — {len(old['rencontres'])} rencontres" if old else "KO"))
    if not old:
        old2=archive_poule('probe','','16',probe_cx,None,phase)
        print("Sans D1 : "+("OK" if old2 else "KO — la saison 2025/2026 n'est réellement plus servie. Abandon."))
        if not old2: return
    ddir=f"data/archive/2025-2026/phase-{phase}/L08SCAN"; os.makedirs(ddir,exist_ok=True)
    found=0
    for cx in range(cx_start,cx_end+1):
        for d1 in d1s:
            res=archive_poule(f'SCAN cx {cx} D1 {d1}',d1,'16',cx,None,phase); time.sleep(0.3)
            if not res: continue
            found+=1
            eqs=[c['equipe'] for c in res['classement']]
            print(f"  cx {cx} (D1 {d1}) : {len(res['rencontres'])} rencontres — {', '.join(eqs[:4])}…")
            json.dump(res, open(f"{ddir}/poule-{cx}.json","w"), ensure_ascii=False)
            break
    print(f"OK — {found} poule(s) récupérée(s) dans {ddir}")

def main():
    if len(sys.argv)>1 and sys.argv[1]=='scan':
        scan(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5].split(',')); return
    phase=sys.argv[1] if len(sys.argv)>1 else '2'
    orgf=sys.argv[2] if len(sys.argv)>2 else 'all'
    eq=fb.get(f"xml_equipe.php?numclu={fb.CLUB}&type=A")
    # divisions ACBB de la phase demandée : D1 -> (libdivision, org, [cx_poules ACBB], poule_num min)
    divs={}
    for mm in re.finditer(r'<equipe>(.*?)</equipe>', eq, re.S):
        b=mm.group(1); lib=tg(b,'libequipe'); ld=tg(b,'libdivision')
        if f'Phase {phase}' not in lib and f'phase {phase}' not in ld and f'Ph{phase}' not in ld and f'_Ph{phase}' not in ld: continue
        if 'CNV' in ld or 'National' in ld or 'Nationale' in ld: continue   # hors national
        m=re.search(r'<liendivision><!\[CDATA\[(.*?)\]\]>',b)
        if not m: continue
        p=dict(x.split('=') for x in html.unescape(m.group(1)).split('&'))
        d1=p.get('D1'); org=p.get('organisme_pere'); cx=int(p.get('cx_poule'))
        if orgf!='all' and org!=orgf: continue
        num=int((re.search(r'[Pp]oule\s*(\d+)', ld) or re.search(r'(\d+)$', ld)).group(1))
        d=divs.setdefault(d1, {'lib':ld,'org':org,'cx':[],'minnum':99})
        d['cx'].append((cx,num)); d['minnum']=min(d['minnum'],num)
    print(f"Phase {phase}, org={orgf} : {len(divs)} divisions ACBB")
    os.makedirs(f"data/archive/2025-2026/phase-{phase}", exist_ok=True)
    tot_p=0; tot_r=0
    for d1,info in divs.items():
        org=info['org']; ld=info['lib']
        cx0,num0=min(info['cx'], key=lambda x:x[1]); base=cx0-(num0-1)
        # poules = scan séquentiel ∪ poules ACBB connues (hors-séquence)
        cand=set(range(base, base+20)) | set(c for c,_ in info['cx'])
        ddir=f"data/archive/2025-2026/phase-{phase}/{slug(ld)}"; os.makedirs(ddir,exist_ok=True)
        found=0; empty=0
        for cx in sorted(cand):
            res=archive_poule(ld,d1,org,cx,None,phase); time.sleep(0.2)
            if not res:
                empty+=1
                if empty>=3 and cx>max(c for c,_ in info['cx']): break
                continue
            empty=0; found+=1; tot_p+=1; tot_r+=len(res['rencontres'])
            res['poule']=found
            json.dump(res, open(f"{ddir}/poule-{cx}.json","w"), ensure_ascii=False)
        print(f"  {ld:42s} -> {found} poules")
    print(f"OK — {tot_p} poules, {tot_r} rencontres archivées (phase {phase}, org {orgf}).")

if __name__=='__main__': main()
