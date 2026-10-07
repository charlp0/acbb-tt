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
    # tables ajoutées en octobre 2026 : critérium (05) et Championnat de Paris (06) ; oubli relevé par l'audit du 07/10
    'criterium_log': 'id', 'cdp_dispos_log': 'id', 'cdp_compo_log': 'id',
}


class ObjectNotFound(RuntimeError):
    """Objet Storage absent, distinct d'un refus d'accès ou d'une panne."""


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
        # Storage peut répondre HTTP 400 avec NoSuchKey/statusCode=404.
        # Ne tolérer que cette absence précise, jamais tous les HTTP 400/404
        # (une erreur de bucket, de droits ou de configuration doit rester visible).
        try:
            detail = json.loads(exc.read(4096))
        except (ValueError, UnicodeError):
            detail = {}
        if not isinstance(detail, dict):
            detail = {}
        missing = detail.get('code') == 'NoSuchKey' or (
            not detail.get('code') and str(detail.get('statusCode')) == '404'
            and detail.get('message') == 'Object not found')
        if (method == 'GET' and path.startswith('/storage/v1/object/authenticated/')
                and exc.code in (400, 404) and missing):
            raise ObjectNotFound('Objet privé introuvable') from None
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
