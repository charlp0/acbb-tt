"""Charge le dernier curseur privé ; seule une absence initiale est tolérée."""
import json
from pathlib import Path
from private_store import get


def main():
    try:
        raw = get('alerts/dispos/cursor.json')
    except RuntimeError as exc:
        if str(exc) != 'Stockage privé : HTTP 404':
            raise
        # Au premier passage, le dernier curseur historique évite de renvoyer
        # toutes les saisies. Il ne contient aucune identité/disponibilité.
        return
    cursor = json.loads(raw)
    if not isinstance(cursor.get('last_id'), int):
        raise RuntimeError('Curseur privé invalide')
    Path('data/dispos_alert_state.json').write_bytes(raw)


if __name__ == '__main__':
    main()
