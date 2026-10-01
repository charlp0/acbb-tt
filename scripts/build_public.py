"""Construit le seul dossier publiable. Un nouveau fichier n'est pas public par défaut."""
import argparse
from pathlib import Path
import shutil
import hashlib
import datetime
import json
from check_data import source_health
from fftt_quality import coverage
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DATA = {
    'teams.json', 'sexes.json', 'scoring.json', 'scoring.js', 'numerotes2526.json', 'meta.json',
    'resultats2627.json', 'tags.json', 'poules2627.json', 'renumerotation2627.json',
    'officiel2627.json', 'capitaines.json', 'salles_domicile2627.json', 'salles2627.json',
    'site.json', 'site.js', 'salles_adverses.json', 'categories.json', 'players_index.json',
    'lieux.json', 'freshness.json',
}
ASSETS = {'bande-noire.png', 'logo.png', 'icon-180.png', 'icon-192.png', 'icon-512.png',
          'icon-maskable-512.png', 'manifest.json', 'sw.js', 'report.js', 'CNAME', 'robots.txt'}


def public_files(root=ROOT):
    files = [p for p in root.glob('*.html')]
    for folder in ('sportive', 'refonte'):
        files.extend((root / folder).rglob('*.html'))
    files.extend(p for p in (root / 'shared').glob('*') if p.suffix in ('.js', '.css'))
    files.extend(root / p for p in ASSETS if (root / p).is_file())
    files.extend(root / 'data' / p for p in DATA if (root / 'data' / p).is_file())
    files.extend(p for p in (root / 'data/players').glob('*.json') if p.stem.isdigit())
    files.extend(p for p in (root / 'data/archive/2025-2026/players').glob('*.json') if p.stem.isdigit())
    for filename in ('players_index.json', 'acbb-vs.json'):
        p = root / 'data/archive/2025-2026' / filename
        if p.is_file():
            files.append(p)
    for p in files:
        if p.is_symlink() or not p.resolve().is_relative_to(root.resolve()):
            raise ValueError('Un lien symbolique ne peut pas être publié')
    return files


def build(root=ROOT, destination=None):
    destination = destination or root / 'build/public'
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for p in public_files(root):
        target = destination / p.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix == '.html':
            def version(m):
                url=m.group(2); parsed=urlsplit(url)
                if parsed.scheme or parsed.netloc: return m.group(0)
                source=(p.parent/parsed.path).resolve()
                if source.suffix not in ('.js','.css') or not source.is_relative_to(root.resolve()) or not source.is_file():return m.group(0)
                digest=hashlib.sha256(source.read_bytes()).hexdigest()[:12]
                return m.group(1)+parsed.path+'?v='+digest+m.group(3)
            target.write_text(re.sub(r'((?:src|href)=["\'])([^"\']+)(["\'])',version,p.read_text()))
        else:
            shutil.copyfile(p, target)
    now=datetime.datetime.now(datetime.timezone.utc)
    (destination/'data/freshness.json').write_text(json.dumps({'checked_at':now.isoformat(),'sources':source_health(root,now),'coverage':coverage(json.loads((root/'data/site.json').read_text()))},ensure_ascii=False))
    (destination / '.nojekyll').touch()
    print('Publication préparée : %d fichiers autorisés.' % len(public_files(root)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    build(destination=args.out)
