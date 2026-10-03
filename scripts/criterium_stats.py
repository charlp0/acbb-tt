# -*- coding: utf-8 -*-
"""Bilans victoires / défaites du critérium : interroge la FFTT et enrichit le fichier publié.

Pour chaque joueur d'un groupe où nous avons quelqu'un, on compte depuis le début de
saison : victoires, défaites, performances et contres — les quatre compteurs de l'appli
FFTT. Aucun point d'entrée ne les rend tout faits (vérifié : ni xml_licence, ni
xml_licence_b, ni xml_joueur ; xml_bilan n'existe pas), la liste des parties est donc la
source et l'agrégation se fait ici.

Définition retenue, celle de la fédération, sans seuil inventé :
  · performance = victoire contre un classement SUPÉRIEUR au sien
  · contre      = défaite contre un classement INFÉRIEUR au sien
Le classement de l'adversaire est dans `advclaof` de chaque partie, le sien dans `clast`
de xml_joueur. Un joueur numéroté (« N176 ») passe avant tout classement par lettre, et
entre numérotés le plus petit rang est le meilleur.

Les licences ne sont pas dans le dépôt : elles viennent de scenarios_log (slot
« criterium_lic »), déposées par scripts/criterium_push_lic.py. Seuls les COMPTEURS
agrégés sont écrits dans le fichier publié, jamais une licence.

Fenetre : la base « parties » de la federation s'arrete fin juin 2026 (sonde du
03/10/2026 : 99 a 172 parties par joueur, aucune posterieure au 21/06/2026). Les
journees de septembre et octobre 2026 n'y sont pas encore. Compter « depuis le debut
de la saison 26/27 » rendait donc zero partout, ce qui etait exact et inutile. On
compte depuis le 01/07/2025, et on publie la derniere date reellement vue pour que la
page dise de quoi elle parle au lieu de le supposer.

Usage : python3 scripts/criterium_stats.py <tour> [debut_saison JJ/MM/AAAA]
Env : FFTT_ID, FFTT_PWD, SUPA_SERVICE_KEY
"""
import json, os, re, sys, time, datetime, urllib.request, importlib.util, threading
from concurrent.futures import ThreadPoolExecutor

SB = "https://vhhmageufrcenruywawg.supabase.co"
SORTIE = 'data/criterium2627.json'
spec = importlib.util.spec_from_file_location("fb", "scripts/fftt_build.py")
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)

def classement(v):
    """Rend un classement comparable : un numéroté passe avant tout classement par
    lettre, et entre numérotés le plus petit rang est le meilleur."""
    v = str(v or '').strip().upper()
    m = re.match(r'^N\s*°?\s*(\d+)', v)
    if m: return 10000 - int(m.group(1))
    m = re.match(r'^(\d+)', v)
    return int(m.group(1)) if m else None

def tags(s):
    return dict(re.findall(r'<([a-zA-Z0-9_]+)>([^<]*)</\1>', s or '', re.S))

def table_licences(tour):
    k = os.environ.get('SUPA_SERVICE_KEY') or ''
    if not k: sys.exit('SUPA_SERVICE_KEY manquant')
    url = (SB + '/rest/v1/scenarios_log?select=tags&slot=eq.criterium_lic'
           '&order=id.desc&limit=1')
    req = urllib.request.Request(url, headers={'apikey': k, 'Authorization': 'Bearer ' + k})
    with urllib.request.urlopen(req) as r:
        lignes = json.load(r)
    if not lignes: sys.exit('aucune table de licences déposée (criterium_push_lic.py)')
    t = lignes[0]['tags']
    if str(t.get('tour')) != str(tour): print('  ⚠️ la table déposée vise le tour %s' % t.get('tour'))
    return t.get('lic') or {}

def bilan(lic, depuis):
    """(v, d, perfs, contres) depuis le début de saison, ou None si la FFTT ne répond pas."""
    try:
        fiche = tags(fb.get('xml_joueur.php?licence=%s' % lic)); time.sleep(0.03)
        moi = classement(fiche.get('clast'))
        brut = fb.get('xml_partie_mysql.php?licence=%s' % lic); time.sleep(0.03)
    except Exception:
        return None
    v = d = pf = ct = 0; vue = None
    for b in re.findall(r'<partie>(.*?)</partie>', brut or '', re.S):
        p = tags(b)
        jj = p.get('date', '')
        if not re.match(r'^\d{2}/\d{2}/\d{4}$', jj): continue
        j, m, a = (int(x) for x in jj.split('/'))
        if datetime.date(a, m, j) < depuis: continue
        q = datetime.date(a, m, j)
        if vue is None or q > vue: vue = q
        gagne = (p.get('vd') or '').upper().startswith('V')
        adv = classement(p.get('advclaof'))
        if gagne:
            v += 1
            if moi is not None and adv is not None and adv > moi: pf += 1
        else:
            d += 1
            if moi is not None and adv is not None and adv < moi: ct += 1
    return v, d, pf, ct, vue

def main():
    tour = sys.argv[1] if len(sys.argv) > 1 else '1'
    dep = sys.argv[2] if len(sys.argv) > 2 else '01/07/2025'
    j, m, a = (int(x) for x in dep.split('/'))
    depuis = datetime.date(a, m, j)
    lic = table_licences(tour)
    doc = json.load(open(SORTIE)); t = doc['tours'][str(tour)]
    # on ne traite que les groupes consultables : la page n'ouvre que ceux où nous jouons
    cibles = [g for g in t['groupes'] if any(x['acbb'] for x in g['joueurs'])]
    besoin = []
    for g in cibles:
        for p in g['joueurs']:
            l = (lic.get(g['id']) or {}).get(str(p.get('pos') or 0))
            if l: besoin.append(l)
    uniques = sorted(set(besoin))
    print('%d groupes consultables · %d joueurs · %d licences distinctes' % (len(cibles), len(besoin), len(uniques)))
    # Deux appels FFTT par licence, un millier de licences : en serie le job depasse
    # l'heure. FILS fils suffisent a tenir dans le quart d'heure sans brusquer la
    # federation (auth() est sans etat, donc parallelisable sans risque).
    FILS = 4
    cache, echecs, faits, verrou = {}, 0, [0], threading.Lock()
    def un(l):
        b = bilan(l, depuis)
        with verrou:
            faits[0] += 1
            if faits[0] % 100 == 0: print('  %d/%d' % (faits[0], len(uniques)), flush=True)
        return l, b
    with ThreadPoolExecutor(max_workers=FILS) as ex:
        for l, b in ex.map(un, uniques):
            if b is None: echecs += 1
            else: cache[l] = b
    pose = 0
    for g in t['groupes']:
        for p in g['joueurs']:
            l = (lic.get(g['id']) or {}).get(str(p.get('pos') or 0))
            b = cache.get(l) if l else None
            for champ in ('v', 'd', 'pf', 'ct'): p.pop(champ, None)
            if b and (b[0] or b[1]):
                p['v'], p['d'], p['pf'], p['ct'] = b[:4]
                pose += 1
    doc['maj'] = datetime.date.today().isoformat()
    vues = [b[4] for b in cache.values() if b[4]]
    jusqu = max(vues).strftime('%d/%m/%Y') if vues else None
    doc['bilans'] = {'depuis': dep, 'jusqu': jusqu, 'le': datetime.date.today().isoformat()}
    print('derniere partie connue de la FFTT : %s' % (jusqu or 'aucune'))
    json.dump(doc, open(SORTIE, 'w'), ensure_ascii=False, indent=1, sort_keys=False)
    print('bilans posés sur %d joueurs · %d licences sans réponse FFTT' % (pose, echecs))

if __name__ == '__main__':
    main()
