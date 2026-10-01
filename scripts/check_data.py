"""Valide les JSON et l'intégrité des relations ; date les sources séparément."""
import argparse
import datetime
import json
from pathlib import Path
from fftt_quality import coverage

ROOT = Path(__file__).resolve().parents[1]


def source_health(root=ROOT, now=None, max_hours=18):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    result = {}
    for label, filename in [('joueurs','meta.json'),('poules','site.json'),('scoring','scoring.json')]:
        data = json.loads((root / 'data' / filename).read_text())
        stamp = data.get('built')
        try:
            dt = datetime.datetime.fromisoformat(stamp.replace('Z','+00:00'))
            if dt.tzinfo is None: dt=dt.replace(tzinfo=datetime.timezone.utc)
            age = (now-dt).total_seconds()/3600
            fresh = 0 <= age <= max_hours
        except (TypeError,ValueError,AttributeError):
            age, fresh = None, False
        result[label] = {'collected_at': stamp, 'age_hours': round(age,1) if age is not None else None, 'fresh': fresh}
    return result


def validate(root=ROOT):
    for p in (root/'data').rglob('*.json'):
        if p.name.startswith('_'): continue
        json.loads(p.read_text())
    index = json.loads((root/'data/players_index.json').read_text())
    for player in index:
        p=root/'data/players'/('%s.json'%player['lic'])
        if not p.exists(): raise ValueError('Index joueur sans fiche')
        profile=json.loads(p.read_text())
        if str(profile['lic'])!=str(player['lic']): raise ValueError('Licence incohérente')
    venues=json.loads((root/'data/lieux.json').read_text())['lieux']
    halls=json.loads((root/'data/salles2627.json').read_text())['salles']
    for value in halls.values():
        for row in value['cal']:
            if row.get('lieu_id') and row['lieu_id'] not in venues: raise ValueError('Lieu inconnu')
            if row.get('salle')=='Bartholdi' and 'piscine' in str(row.get('venue','')).lower(): raise ValueError('Bartholdi porte encore une adresse de piscine')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--write-freshness',action='store_true')
    parser.add_argument('--require-fresh',action='store_true')
    args=parser.parse_args()
    validate()
    now=datetime.datetime.now(datetime.timezone.utc)
    sources=source_health(now=now)
    if args.write_freshness:
        site=json.loads((ROOT/'data/site.json').read_text())
        (ROOT/'data/freshness.json').write_text(json.dumps({'checked_at':now.isoformat(),'sources':sources,'coverage':coverage(site)},ensure_ascii=False))
    if args.require_fresh and not all(v['fresh'] for v in sources.values()):
        raise SystemExit('Source(s) FFTT périmée(s) : '+', '.join(k for k,v in sources.items() if not v['fresh']))
    print('Relations des données et adresses vérifiées.')


if __name__=='__main__': main()
