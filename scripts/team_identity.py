"""Rapprochements prudents : numéro d'équipe ET mots distinctifs, jamais TT/AS."""
import re
import unicodedata

GENERIC = set('TT AS US CS ES AC CSM USM SC ATT UMS SMTT VGA ESP STT CTT SM TTM TTMC EP ASTT PPC CTTA MJC ASC ASV ASVTT SCTT SPORT SPORTS CLUB TENNIS TABLE PING'.split())


def words(s):
    s = unicodedata.normalize('NFD', str(s or '')).encode('ascii', 'ignore').decode().upper()
    return re.findall(r'[A-Z0-9]+', s)


def identity(s):
    w = words(s)
    if not w or not w[-1].isdigit():
        return None
    return w[-1], frozenset(x for x in w[:-1] if x not in GENERIC)


def same_team(a, b):
    if words(a) == words(b):
        return True
    ka, kb = identity(a), identity(b)
    return bool(ka and kb and ka[0] == kb[0] and ka[1] and ka[1] == kb[1])


def unique_alias(name, candidates):
    hits = [s for s in candidates if same_team(name, s)]
    return hits[0] if len(hits) == 1 else None
