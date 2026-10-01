import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import private_store
import restore_alert_cursor
import publish_private_alert


class AlertCursorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        cwd = os.getcwd()
        os.chdir(self.temp.name)
        self.addCleanup(os.chdir, cwd)
        Path('data').mkdir()
        self.state = Path('data/dispos_alert_state.json')
        self.state.write_text('{"last_id":294}')
        env = patch.dict(os.environ, {'SUPA_SERVICE_KEY': 'test-only-not-a-secret'})
        env.start()
        self.addCleanup(env.stop)

    def error(self, status, detail):
        return urllib.error.HTTPError('https://example.invalid/storage', status, 'Error', {},
                                      io.BytesIO(json.dumps(detail).encode()))

    def test_first_run_missing_object_keeps_historical_cursor_then_initializes_private_cursor(self):
        missing = {'code': 'NoSuchKey', 'statusCode': '404', 'error': 'not_found', 'message': 'Object not found'}
        with patch('private_store.urllib.request.urlopen', side_effect=self.error(400, missing)):
            restore_alert_cursor.main()
        self.assertEqual(json.loads(self.state.read_text())['last_id'], 294)
        # Sans changement de disponibilité, aucun avis n'est publié. La dernière
        # étape du workflow initialise tout de même le curseur privé.
        with patch('publish_private_alert.put') as put, contextlib.redirect_stdout(io.StringIO()):
            with patch.object(sys, 'argv', ['publish_private_alert.py']):
                publish_private_alert.main()
            put.assert_not_called()
            with patch.object(sys, 'argv', ['publish_private_alert.py', '--commit-cursor']):
                publish_private_alert.main()
            self.assertEqual(put.call_args.args[0], 'alerts/dispos/cursor.json')
            private_cursor = put.call_args.args[1]
        self.state.write_text('{"last_id":0}')
        with patch('restore_alert_cursor.get', return_value=private_cursor):
            restore_alert_cursor.main()
        self.assertEqual(json.loads(self.state.read_text())['last_id'], 294)

    def test_legacy_not_found_response_is_recognized(self):
        with patch('private_store.urllib.request.urlopen', side_effect=self.error(
                404, {'statusCode': '404', 'message': 'Object not found'})):
            restore_alert_cursor.main()
        self.assertEqual(json.loads(self.state.read_text())['last_id'], 294)

    def test_auth_bucket_server_and_other_bad_requests_fail_without_resetting_cursor(self):
        for status, detail in [(401, {'message': 'Unauthorized'}),
                               (403, {'code': 'AccessDenied'}),
                               (400, {'code': 'NoSuchBucket'}),
                               (400, {'code': 'InvalidRequest', 'message': 'private detail'}),
                               (404, {}), (500, {'code': 'NoSuchKey'})]:
            with self.subTest(status=status, detail=detail):
                with patch('private_store.urllib.request.urlopen', side_effect=self.error(status, detail)):
                    with self.assertRaises(RuntimeError) as caught:
                        restore_alert_cursor.main()
                self.assertNotIsInstance(caught.exception, private_store.ObjectNotFound)
                self.assertEqual(str(caught.exception), 'Stockage privé : HTTP %s' % status)
                self.assertEqual(json.loads(self.state.read_text())['last_id'], 294)

    def test_invalid_remote_cursor_never_replaces_local_state(self):
        for cursor in [{}, {'last_id': True}, {'last_id': -1}, {'last_id': '295'}, []]:
            with self.subTest(cursor=cursor), patch('restore_alert_cursor.get', return_value=json.dumps(cursor).encode()):
                with self.assertRaises(RuntimeError):
                    restore_alert_cursor.main()
                self.assertEqual(json.loads(self.state.read_text())['last_id'], 294)


if __name__ == '__main__':
    unittest.main()
