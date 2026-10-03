import ast
import copy
import datetime
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from fftt_quality import profile_signature, check_site, acbb_team_key, require_xml, retry_missing_pools, coverage
import fftt_site
from team_identity import same_team, unique_alias
from backup_private import encode, verify, main as backup
from private_store import rows, TABLES
from check_data import source_health
from build_public import public_files


class DataTests(unittest.TestCase):
    def test_ranking_and_homologation_invalidate_cache(self):
        m='<partie><idpartie>1</idpartie><victoire>V</victoire><classement>900</classement></partie>'
        base=profile_signature(m,'<pointm>1000</pointm>','')
        self.assertNotEqual(base,profile_signature(m,'<pointm>1020</pointm>',''))
        self.assertNotEqual(base,profile_signature(m.replace('900','920'),'<pointm>1000</pointm>',''))
        self.assertNotEqual(base,profile_signature(m,'<pointm>1000</pointm>','<partie><idpartie>1</idpartie><pointres>7</pointres></partie>'))

    def test_missing_previously_known_sheet_cancels_publication(self):
        old={'DATA':{'M11':{'teams':[{'name':'ACBB 11','acbb':True,'journees':[{'journee':1,'players':[{}],'match_score':22}]}]}}}
        new={'DATA':{'M11':{'teams':[{'name':'ACBB 11','acbb':True,'journees':[]}]}}}
        with self.assertRaises(ValueError): check_site(old,new,['M11'])
        with self.assertRaises(ValueError): check_site({},new,['M11','M9'])
        check_site(old,old,['M11'])

    def test_generic_club_words_and_team_numbers_never_match(self):
        self.assertFalse(same_team('AS PARIS 2','AS NANTERRE 2'))
        self.assertFalse(same_team('COURBEVOIE STT 4','COURBEVOIE STT 5'))
        self.assertFalse(same_team('PING PARIS 14 1','PARIS US 1'))
        self.assertTrue(same_team('USM MALAKOFF 5','MALAKOFF USM 5'))
        self.assertIsNone(unique_alias('MALAKOFF 5',['MALAKOFF USM 5','USM MALAKOFF 5']))

    def test_transient_missing_sheet_retries_only_affected_pool(self):
        old={'DATA':{t:{'teams':[{'name':t,'acbb':True,'journees':[
            {'journee':1,'players':[{'nom':'TEST'}],'match_score':22}]}]}
            for t in ['M10','M11']},'STANDINGS':{'M10':[],'M11':[]}}
        current=copy.deepcopy(old)
        current['DATA']['M11']['teams'][0]['journees'][0]['players']=[]
        fresh=copy.deepcopy(old['DATA']['M11'])
        fresh['teams'][0]['journees'].append({'journee':2,'players':[{'nom':'TEST'}],'match_score':24})
        calls=[]
        def collect(key):
            calls.append(key)
            return fresh,[{'name':'M11','mp':2}]
        retry_missing_pools(old,current,collect,pause=lambda _:None)
        self.assertEqual(calls,['M11'])
        self.assertEqual(len(current['DATA']['M11']['teams'][0]['journees']),2)
        self.assertEqual(current['STANDINGS']['M11'][0]['mp'],2)
        check_site(old,current,['M10','M11'])

    def test_existing_sheet_with_games_survives_missing_global_score(self):
        old={'DATA':{'M14':{'teams':[{'name':'ACBB 14','acbb':True,'journees':[
            {'journee':2,'players':[{'nom':'TEST'}],'match_score':10,'opp_score':8}]}]}}}
        current=copy.deepcopy(old)
        row=current['DATA']['M14']['teams'][0]['journees'][0]
        del row['match_score'];del row['opp_score'];row['played_games']=6
        check_site(old,current,['M14'])
        status=coverage(current)
        self.assertEqual(status['with_sheet'],1)
        self.assertEqual(status['pending_sheets'],[])
        self.assertEqual(len(status['pending_scores']),1)
        row['played_games']=0
        with self.assertRaises(ValueError):check_site(old,current,['M14'])

    def test_collector_keeps_sheet_evidence_without_inventing_score(self):
        calendar='''<liste><tour><equa>PUTEAUX 4</equa><equb>BOULOGNE BILLAN 14</equb>
          <libelle>tour n°2</libelle><scorea></scorea><scoreb></scoreb>
          <dateprevue>02/10/2026</dateprevue><lien><![CDATA[id=test]]></lien></tour></liste>'''
        sheet='''<liste><equa>PUTEAUX 4</equa><equb>BOULOGNE BILLAN 14</equb>
          <joueur><xja>ADVERSE Alex</xja><xca>M 1000pts</xca><xjb>TEST Sam</xjb><xcb>M 1100pts</xcb></joueur>
          <partie><ja>ADVERSE Alex</ja><jb>TEST Sam</jb><scorea>1</scorea><scoreb>2</scoreb></partie>
          <partie><ja>ADVERSE Alex</ja><jb>TEST Sam</jb><scorea>0</scorea><scoreb>0</scoreb></partie></liste>'''
        with patch.object(fftt_site.fb,'get',side_effect=[calendar,sheet]),patch.object(fftt_site.time,'sleep'):
            pool=fftt_site.build_pool('M14','test','test','test')
        row=next(t for t in pool['teams'] if t.get('acbb'))['journees'][0]
        self.assertEqual(row['played_games'],1)
        self.assertEqual(row['players'][0]['vic'],1)
        self.assertNotIn('match_score',row)
        self.assertNotIn('opp_score',row)

    def test_persistent_missing_sheet_still_fails_after_bounded_retries(self):
        old={'DATA':{'M11':{'teams':[{'name':'ACBB 11','acbb':True,'journees':[
            {'journee':1,'players':[{'nom':'TEST'}],'match_score':22}]}]}},'STANDINGS':{}}
        current=copy.deepcopy(old)
        current['DATA']['M11']['teams'][0]['journees'][0]['players']=[]
        calls=[]
        def collect(key):
            calls.append(key)
            return current['DATA'][key],[]
        retry_missing_pools(old,current,collect,pause=lambda _:None)
        self.assertEqual(calls,['M11','M11'])
        with self.assertRaisesRegex(ValueError,'M11 / ACBB 11 / J1.*publication refusée'):
            check_site(old,current,['M11'])

    def test_backup_pagination_exceeds_supabase_default_page(self):
        data=[{'id':n} for n in range(1201)]
        def fake(path,*args):
            import urllib.parse
            query=urllib.parse.parse_qs(urllib.parse.urlparse(path).query)
            offset=int(query['offset'][0]);limit=int(query['limit'][0])
            return json.dumps(data[offset:offset+limit]).encode()
        with patch('private_store.request',side_effect=fake) as req:
            self.assertEqual(rows('dispos_log'),data)
            self.assertEqual(req.call_count,3)

    def test_backup_roundtrip_and_public_bucket_refusal(self):
        tables={table:[] for table in TABLES}
        tables['scenarios_log']=[{'id':1,'slot':'j1','tags':{'M11':{'p':['101']}}}]
        blob=encode(tables,'start','end');self.assertEqual(verify(blob)['tables'],tables)
        with patch('backup_private.request',return_value=b'{"public":true}'),patch('backup_private.rows') as read:
            with self.assertRaises(RuntimeError):backup()
            read.assert_not_called()

    def test_health_checks_every_source_not_just_profiles(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'data').mkdir()
            for name,stamp in [('meta.json','2026-09-30T10:00:00Z'),('site.json','2026-09-28T10:00:00Z'),('scoring.json','2026-09-30T09:00:00Z')]:
                (root/'data'/name).write_text(json.dumps({'built':stamp}))
            health=source_health(root,datetime.datetime(2026,9,30,12,tzinfo=datetime.timezone.utc))
            self.assertTrue(health['joueurs']['fresh']);self.assertFalse(health['poules']['fresh'])

    def test_new_file_is_not_public_by_default(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in ['index.html','data/meta.json','data/private-notes.json','data/backup-supabase/dispos_log.json','private.csv']:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('{}')
            published={str(p.relative_to(root)) for p in public_files(root)}
            self.assertEqual(published,{'index.html','data/meta.json'})

    def test_team_identity_separates_men_and_women(self):
        label='BOULOGNE BILLANCOURT AC 2 - Phase 1'
        self.assertEqual(acbb_team_key(label,'FED_Nationale 1 Messieurs Phase 1 Poule 2'),'M2')
        self.assertEqual(acbb_team_key(label,'Régionale 1 Dames Poule 3'),'F2')
        self.assertIsNone(acbb_team_key(label,'Division inconnue'))

    def test_malformed_or_error_xml_is_never_a_success(self):
        self.assertEqual(require_xml('<liste/>'),'<liste/>')
        for value in ['<liste>','<html>maintenance</html>','<liste><erreur>indisponible</erreur></liste>']:
            with self.assertRaises(ValueError):require_xml(value)

    def test_all_python_scripts_parse(self):
        for p in (ROOT/'scripts').glob('*.py'):
            ast.parse(p.read_text(),filename=p.name)


if __name__=='__main__':unittest.main()
