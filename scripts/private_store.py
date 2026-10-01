"""Accès service aux sauvegardes privées. Aucune valeur sensible dans les logs."""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

BUCKET = 'club-backups'
TABLES = {
    'tags_log': 'id', 'scenarios_log': 'id', 'dispos_log': 'id',
    'gate_log': 'id', 'signalements_log': 'id', 'licences_valides': 'licence',
    'liens': 'id', 'naissances': 'licence', 'tentatives': 'id',
    'appareils': 'device_id,licence', 'debriefs_log': 'id', 'journal': 'id',
    'liens_usages': 'lien_id,device_id', 'private_config': 'name',
}


def request(path, method='GET', data=None, content_type='application/json'):
    secret = os.environ.get('SUPA_SERVICE_KEY')
    if not secret:
        raise RuntimeError('SUPA_SERVICE_KEY manquante')
    base = os.environ.get('SUPABASE_URL', 'https://vhhmageufrcenruywawg.supabase.co').rstrip('/')
    req = urllib.request.Request(base + path, data=data, method=method, headers={
        'apikey': secret, 'Authorization': 'Bearer ' + secret,
        'Content-Type': content_type, 'x-upsert': 'true',
    })
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        # Ne pas recopier l'URL, le corps de la réponse ou les données envoyées.
        raise RuntimeError('Stockage privé : HTTP %s' % exc.code) from None


def rows(table, order=None, query='select=*'):
    """Pagination explicite, ordre stable. Les journaux sont append-only."""
    if table not in TABLES:
        raise ValueError('table non autorisée')
    order = order or TABLES[table]
    out, offset, size = [], 0, 500
    while True:
        part = json.loads(request('/rest/v1/%s?%s&order=%s&offset=%d&limit=%d' %
                                 (table, query, order, offset, size)))
        if not isinstance(part, list):
            raise RuntimeError('Réponse de sauvegarde invalide')
        out.extend(part)
        if len(part) < size:
            return out
        offset += len(part)


def put(path, content, content_type='application/json'):
    return request('/storage/v1/object/%s/%s' % (BUCKET, urllib.parse.quote(path, safe='/')),
                   'POST', content, content_type)


def get(path):
    return request('/storage/v1/object/authenticated/%s/%s' % (BUCKET, urllib.parse.quote(path, safe='/')))
