"""Diagnostic en lecture seule des feuilles J2 M14/M16, sans données joueurs."""
import html
import json
import re
import fftt_site as site
from fftt_quality import acbb_team_key

fb, tg = site.fb, site.tg
equipes = fb.get(f'xml_equipe.php?numclu={fb.CLUB}&type=A')
for block in re.findall(r'<equipe>(.*?)</equipe>', equipes, re.S):
    key = acbb_team_key(tg(block, 'libequipe'), tg(block, 'libdivision'))
    if key not in ('M14', 'M16') or 'Phase 1' not in tg(block, 'libequipe'):
        continue
    link = re.search(r'<liendivision><!\[CDATA\[(.*?)\]\]>', block)
    if not link:
        raise RuntimeError('Lien de poule manquant : ' + key)
    calendar = fb.get('xml_result_equ.php?' + html.unescape(link.group(1)))
    for match in re.findall(r'<tour>(.*?)</tour>', calendar, re.S):
        ea, eb = tg(match, 'equa'), tg(match, 'equb')
        round_no = re.search(r'tour\s*n°?\s*(\d+)', tg(match, 'libelle'))
        if not round_no or int(round_no.group(1)) != 2 or not (site.is_acbb(ea) or site.is_acbb(eb)):
            continue
        detail = re.search(r'<lien><!\[CDATA\[(.*?)\]\]>', match)
        report = dict(team=key, equa=ea, equb=eb, scorea=tg(match,'scorea'), scoreb=tg(match,'scoreb'),
                      has_detail_link=bool(detail), date=tg(match,'datereelle'))
        if detail:
            raw = fb.get('xml_chp_renc.php?' + html.unescape(detail.group(1)))
            report['sheet'] = {k:tg(raw,k) for k in ('equa','equb','scorea','scoreb')}
            report['player_rows'] = len(re.findall(r'<joueur>',raw))
            report['game_rows'] = len(re.findall(r'<partie>',raw))
            report['tags'] = sorted(set(re.findall(r'<([a-zA-Z0-9_]+)>',raw)))
            report['team_names_match'] = sorted([fb.nrm(ea),fb.nrm(eb)]) == sorted([fb.nrm(tg(raw,'equa')),fb.nrm(tg(raw,'equb'))])
        print(json.dumps(report,ensure_ascii=False),flush=True)
