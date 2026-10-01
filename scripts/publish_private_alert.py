"""Archive un avis dans Storage privé, puis avance le curseur seulement si vérifié."""
import json
import pathlib
import sys
from private_store import put, get


def main():
    body = pathlib.Path('alert.md')
    state = pathlib.Path('data/dispos_alert_state.json')
    if not state.exists():
        return
    cursor = json.loads(state.read_text())
    if '--commit-cursor' in sys.argv:
        put('alerts/dispos/cursor.json', json.dumps(cursor).encode())
        return
    if body.exists():
        data = json.dumps({'cursor': cursor, 'message': body.read_text()}, ensure_ascii=False).encode()
        path = 'alerts/dispos/%s.json' % cursor['last_id']
        put(path, data)
        if get(path) != data:
            raise RuntimeError('Avis privé non vérifié : curseur conservé')
        put('alerts/dispos/latest.json', data)
    print('Avis privé enregistré ; curseur en attente de notification.')


if __name__ == '__main__':
    main()
