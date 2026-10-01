"""Sauvegarde complète des tables, privée et vérifiée après téléchargement.

Pas de commit ni d'artifact GitHub : le fichier gzip reste dans Storage privé.
Les tables sont collectées entre started_at et ended_at (pas un instantané SQL).
Les références des photos sont sauvegardées ; leurs objets restent dans leurs buckets.
"""
import datetime
import gzip
import hashlib
import json
from private_store import TABLES, rows, put, get, request, BUCKET


def encode(tables, started_at, ended_at):
    payload = {'format': 1, 'started_at': started_at, 'ended_at': ended_at, 'tables': tables}
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    return gzip.compress(raw, mtime=0)


def verify(blob):
    data = json.loads(gzip.decompress(blob))
    if data.get('format') != 1 or not isinstance(data.get('tables'), dict):
        raise ValueError('Format de sauvegarde invalide')
    if set(data['tables']) != set(TABLES) or any(not isinstance(v, list) for v in data['tables'].values()):
        raise ValueError('Sauvegarde incomplète')
    return data


def main():
    bucket = json.loads(request('/storage/v1/bucket/' + BUCKET))
    if bucket.get('public') is not False:
        raise RuntimeError('Refus : le bucket de sauvegarde doit être privé')
    started = datetime.datetime.now(datetime.timezone.utc)
    tables = {table: rows(table) for table in TABLES}
    ended = datetime.datetime.now(datetime.timezone.utc)
    blob = encode(tables, started.isoformat(), ended.isoformat())
    verify(blob)
    path = 'database/' + started.strftime('%Y/%m/%d/%H%M%S') + '.json.gz'
    put(path, blob, 'application/gzip')
    downloaded = get(path)
    if hashlib.sha256(downloaded).digest() != hashlib.sha256(blob).digest():
        raise RuntimeError('La relecture de sauvegarde ne correspond pas')
    verify(downloaded)
    manifest = {'path': path, 'sha256': hashlib.sha256(blob).hexdigest(), 'ended_at': ended.isoformat(),
                'tables': {k: len(v) for k, v in tables.items()}}
    put('database/latest.json', json.dumps(manifest).encode())
    print('Sauvegarde privée complète ; intégrité vérifiée après relecture.')


if __name__ == '__main__':
    main()
