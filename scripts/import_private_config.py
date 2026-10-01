"""Migration explicite de la source locale vers private_config. Rien par défaut.

Usage : python3 scripts/import_private_config.py /chemin/prive/fichier.json [--apply]
Fournir SUPA_SERVICE_KEY depuis le fichier privé habituel, jamais en argument.
"""
import argparse
import json
from pathlib import Path
from private_store import request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    value = json.loads(args.file.read_text())
    if not isinstance(value.get('ex'), dict) or not isinstance(value.get('a_confirmer'), dict):
        raise ValueError('Configuration invalide')
    if not args.apply:
        print('Configuration valide. Aucune écriture effectuée (ajouter --apply pour importer).')
        return
    # PUT avec clé primaire : idempotent et sans valeurs personnelles dans la sortie.
    payload = json.dumps({'name': 'extra_communautaires', 'value': value}).encode()
    request('/rest/v1/private_config?name=eq.extra_communautaires', 'PUT', payload)
    back = json.loads(request('/rest/v1/private_config?name=eq.extra_communautaires&select=value'))
    if len(back) != 1 or back[0]['value'] != value:
        raise RuntimeError('La vérification de migration a échoué')
    print('Configuration privée importée et relue.')


if __name__ == '__main__':
    main()
