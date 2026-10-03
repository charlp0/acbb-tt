"""Contrôles indépendants de l'API : cache et régressions des données publiées."""
import hashlib
import json
import re


def profile_signature(matches, licence='', validated='', details=None):
    # Tous les champs d'une partie comptent, y compris classement/coefficients et
    # homologation. Un ID et une victoire identiques ne signifient pas « inchangé ».
    parties = lambda xml: sorted(re.findall(r'<partie>(.*?)</partie>', xml, re.S))
    fields = ['point', 'pointm', 'apointm', 'initm', 'sexe', 'num']
    ranks = {f: re.findall(r'<%s>(.*?)</%s>' % (f, f), licence, re.S) for f in fields}
    raw = json.dumps([parties(matches), parties(validated), ranks, details], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def sheet_keys(site):
    return {(t, row.get('name'), int(j['journee']))
            for t, pool in site.get('DATA', {}).items()
            for row in pool.get('teams', []) for j in row.get('journees', [])
            if (j.get('match_score') is not None or j.get('played_games', 0) > 0) and j.get('players')}


def missing_sheets(previous, current):
    return sorted(sheet_keys(previous) - sheet_keys(current))


def describe_sheets(sheets):
    # Noms d'équipes et journées seulement, jamais les joueurs ni les accès API.
    return '; '.join('%s / %s / J%s' % item for item in sheets)


def retry_missing_pools(previous, current, collect_pool, attempts=2, pause=None):
    """Relit seulement les poules incomplètes, sans réutiliser une ancienne feuille.

    Chaque tentative remplace le lot de la poule en entier. Les contrôles finaux
    restent obligatoires : une régression persistante interdit toute écriture.
    """
    import time
    pause = pause or time.sleep
    for attempt in range(1, attempts + 1):
        lost = missing_sheets(previous, current)
        if not lost:
            return
        print('Feuilles absentes, nouvelle lecture %d/%d : %s' %
              (attempt, attempts, describe_sheets(lost)), flush=True)
        pause(2 * attempt)
        for key in sorted({t for t, _, _ in lost}):
            pool, standings = collect_pool(key)
            current['DATA'][key] = pool
            current['STANDINGS'][key] = standings


def check_site(previous, current, expected):
    missing = set(expected) - set(current.get('DATA', {}))
    if missing:
        raise ValueError('Poules FFTT absentes : ' + ', '.join(sorted(missing)))
    lost = missing_sheets(previous, current)
    if lost:
        raise ValueError('%d feuille(s) précédemment connue(s) manquante(s) : %s — publication refusée' %
                         (len(lost), describe_sheets(lost)))
    for t, pool in current['DATA'].items():
        if not pool.get('teams') or not any(x.get('acbb') for x in pool['teams']):
            raise ValueError('Poule sans équipe ACBB : ' + t)
        if previous.get('STANDINGS', {}).get(t) and not current.get('STANDINGS', {}).get(t):
            raise ValueError('Classement précédemment connu manquant : ' + t)


def coverage(site):
    played, available = 0, 0
    pending, pending_scores = [], []
    for t, pool in site.get('DATA', {}).items():
        for row in pool.get('teams', []):
            for j in row.get('journees', []):
                if j.get('match_score') is not None or j.get('played_games', 0) > 0:
                    played += 1
                    if j.get('players'):
                        available += 1
                    else:
                        pending.append({'poule': t, 'equipe': row.get('name'), 'j': j.get('journee')})
                    if j.get('match_score') is None:
                        pending_scores.append({'poule': t, 'equipe': row.get('name'), 'j': j.get('journee')})
    return {'scored_team_rounds': played-len(pending_scores), 'with_sheet': available,
            'pending_sheets': pending, 'pending_scores': pending_scores}


def acbb_team_key(label, division):
    """Le même libellé FFTT existe en messieurs et dames : jamais le nom seul."""
    import unicodedata
    div = ''.join(c for c in unicodedata.normalize('NFKD', division).lower() if not unicodedata.combining(c))
    female = any(x in div for x in ('dames', 'feminin'))
    male = any(x in div for x in ('messieurs', 'masculin', 'pro b'))
    if female == male:
        return None
    base = re.split(r'\s*-\s*Phase\s*\d+', label, flags=re.I)[0].strip()
    n = re.search(r'(\d+)\s*$', base)
    return ('F' if female else 'M') + n.group(1) if n else None


def require_xml(text):
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        raise ValueError('Réponse FFTT XML invalide') from None
    if root.tag.lower() == 'html' or any(e.tag.lower() in ('erreur', 'error') for e in root.iter()):
        raise ValueError('Réponse FFTT en erreur')
    return text
