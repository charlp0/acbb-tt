"""Empêche un retour des sauvegardes, secrets ou pièces privées dans le site."""
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit
from pathlib import Path
from build_public import ROOT, public_files

FORBIDDEN = ('backup-supabase', 'extra_communautaires.json', 'phones.enc.json', '.env',
             '.git/', 'acbb-liens', 'licences-acbb', 'private_config', '.csv', '.xlsx')
# Les marqueurs sont séparés pour que le scanner puisse aussi contrôler son propre code.
SECRET = re.compile(r'(?:' + 'sb_' + r'secret_[A-Za-z0-9_-]{12,}|' + 'sb' + r'p_[A-Za-z0-9]{15,}|' +
                    'eyJhb' + r'GciOi[A-Za-z0-9_.-]{30,}|' + 'Zu54' + 'WakeT8|' + 'SW' + '015' + r')')


def check_public(path=ROOT/'build/public'):
    approved={str(p.relative_to(ROOT)) for p in public_files()}
    approved.update({'.nojekyll','data/freshness.json'})
    failures=[]
    for p in path.rglob('*'):
        if not p.is_file(): continue
        rel=p.relative_to(path).as_posix()
        if rel not in approved or any(word in rel.lower() for word in FORBIDDEN):
            failures.append(rel+': fichier non autorisé')
        if p.suffix in ('.js','.json','.html','.css','.txt'):
            text=p.read_text()
            if SECRET.search(text): failures.append(rel+': marqueur secret détecté')
    class Assets(HTMLParser):
        def handle_starttag(self,tag,attrs):
            attrs=dict(attrs)
            url=attrs.get('src') if tag in ('script','img') else attrs.get('href') if tag=='link' and attrs.get('rel') in ('stylesheet','icon','manifest','apple-touch-icon') else None
            if not url:return
            parsed=urlsplit(url)
            if parsed.scheme or parsed.netloc or not parsed.path:return
            target=(path/parsed.path.lstrip('/')) if parsed.path.startswith('/') else (page.parent/parsed.path)
            if not target.resolve().is_relative_to(path.resolve()) or not target.is_file():
                failures.append(str(page.relative_to(path))+': ressource locale absente '+parsed.path)
    for page in path.rglob('*.html'):
        Assets().feed(page.read_text())
    if failures:
        # Les valeurs sensibles ne sont jamais incluses dans le rapport.
        raise ValueError('\n'.join(failures))
    print('Périmètre public vérifié ; aucune sauvegarde privée ni clé détectée.')


if __name__=='__main__': check_public()
