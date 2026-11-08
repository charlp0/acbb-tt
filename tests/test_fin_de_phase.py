import json
from pathlib import Path
import random
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import fin_de_phase as fdp

# Alignement de contrôle partagé avec tests/fin-de-phase.test.js : même valeur attendue des deux côtés.
LA = [{'cls': 1600, 'adj': 20}, {'cls': 1500, 'adj': 0}, {'cls': 1450, 'adj': -30}, {'cls': 1400, 'adj': 0}]
LB = [{'cls': 1550, 'adj': 0}, {'cls': 1500, 'adj': 10}, {'cls': 1480, 'adj': 0}, {'cls': 1300, 'adj': 0}]
EXPECTED_SINGLES_S400 = 6.3933


class FinDePhaseTests(unittest.TestCase):
    def test_expected_singles_matches_js_control_value(self):
        self.assertAlmostEqual(fdp.expected_singles(LA, LB, 400.0), EXPECTED_SINGLES_S400, places=3)
        # un joueur absent : ses trois simples sont perdus
        self.assertLess(fdp.expected_singles(LA[:3], LB, 400.0), EXPECTED_SINGLES_S400 - 0.5)
        self.assertGreater(fdp.expected_singles(LA, LB[:3], 400.0), EXPECTED_SINGLES_S400 + 0.5)

    def test_parties_from_sheets_uses_individual_wins_then_scores(self):
        ja = {'played_games': 14, 'match_score': 22, 'opp_score': 20, 'doubles': 1, 'players': [{'vic': 2}, {'vic': 2}, {'vic': 2}, {'vic': 1}]}
        jb = {'played_games': 14, 'match_score': 20, 'opp_score': 22, 'doubles': 1, 'players': [{'vic': 1}, {'vic': 2}, {'vic': 1}, {'vic': 1}]}
        self.assertEqual(fdp.parties_from_sheets(ja, jb), (8, 6))
        # championnat national : pas de parties individuelles publiées, le score est déjà en parties
        na = {'played_games': 0, 'match_score': 8, 'opp_score': 1, 'doubles': 0, 'players': [{'vic': 0}] * 4}
        nb = {'played_games': 0, 'match_score': 1, 'opp_score': 8, 'doubles': 0, 'players': [{'vic': 0}] * 4}
        self.assertEqual(fdp.parties_from_sheets(na, nb), (8, 1))
        self.assertEqual(fdp.parties_from_sheets(nb, na), (1, 8))
        self.assertIsNone(fdp.reels(na['players'] and [{'nom': 'X', 'cls': 2000, 'vic': 0}], na)[0]['vic'])

    def test_ranking_article_14(self):
        teams = ['A', 'B', 'C']
        pts = {'A': 10, 'B': 10, 'C': 4}
        # A et B à égalité : B a battu A → B devant malgré un écart total de parties inférieur
        mini = {'A': {'B': (1, -2), 'C': (3, 10)}, 'B': {'A': (3, 2), 'C': (3, 4)}, 'C': {'A': (1, -10), 'B': (1, -4)}}
        diff = {'A': 8, 'B': 6, 'C': -14}
        self.assertEqual(fdp.rank_teams(teams, pts, mini, diff), ['B', 'A', 'C'])
        # sans confrontation : écart de parties total
        mini2 = {'A': {}, 'B': {}, 'C': {}}
        self.assertEqual(fdp.rank_teams(teams, pts, mini2, diff), ['A', 'B', 'C'])

    def test_quotas_and_goal(self):
        q = fdp.quotas_for('L08_R2 Messieurs phase 1 Poule 3')
        self.assertEqual((q['code'], q['up'], q['down'], q['risk']), ('R2', 1, 1, 1))
        self.assertEqual(fdp.goal_reached(1, 8, q, 'montee'), 1)
        self.assertEqual(fdp.goal_reached(2, 8, q, 'montee'), 0)
        self.assertEqual(fdp.goal_reached(6, 8, q, 'maintien'), 1)
        self.assertEqual(fdp.goal_reached(7, 8, q, 'maintien'), 0)
        d2 = fdp.quotas_for('D92_D2 Messieurs_Ph1 Poule 4')
        self.assertEqual(d2['up'], 0)
        # D2 : art. IV.2.3 CD92, 32 maintiens sur 42 → le dernier et une partie des 6ᵉ descendent ; maintien sûr = top 5
        self.assertEqual(fdp.goal_reached(5, 7, d2, 'maintien'), 1)
        self.assertEqual(fdp.goal_reached(6, 7, d2, 'maintien'), 0)
        self.assertAlmostEqual(fdp.descent_probability([0, 0, 0, 0, 0, 0.5, 0.5, 0], 8, q), 0.25)
        self.assertAlmostEqual(fdp.descent_probability([0, 0, 0, 0, 0, 0, 0.5, 0.5], 8, q), 0.75)

    def test_ratings_follow_results(self):
        la = [{'nom': 'A%d' % i, 'prenom': '', 'cls': 1500, 'vic': 2} for i in range(4)]
        P = {'teams': ['X', 'Y', 'Z'], 'played': [
            {'j': 1, 'a': 'X', 'b': 'Y', 'wa': 11, 'wb': 3, 'la': la, 'lb': la},
            {'j': 2, 'a': 'Y', 'b': 'Z', 'wa': 10, 'wb': 4, 'la': la, 'lb': la},
        ]}
        r, _ = fdp.fit_ratings(P, 400.0)
        self.assertGreater(r['X'], r['Y'])
        self.assertGreater(r['Y'], r['Z'])
        self.assertGreater(r['X'] - r['Z'], 200)

    def test_end_to_end_on_synthetic_pool(self):
        players = lambda base, vic: [{'nom': 'P%d%d' % (base, i), 'prenom': 'x', 'cls': base - 40 * i, 'vic': vic} for i in range(4)]
        names = ['FORT 1', 'MOYEN 1', 'BOULOGNE BILLAN 9', 'FAIBLE 1']
        strength = {'FORT 1': 1700, 'MOYEN 1': 1400, 'BOULOGNE BILLAN 9': 1380, 'FAIBLE 1': 1000}
        rounds = [[(0, 1), (2, 3)], [(0, 2), (1, 3)], [(0, 3), (1, 2)]]
        teams = [{'name': n, 'acbb': n.startswith('BOULOGNE'), 'journees': []} for n in names]
        for ri, pairs in enumerate(rounds):
            for a, b in pairs:
                for me, other in ((a, b), (b, a)):
                    mine, theirs = strength[names[me]], strength[names[other]]
                    win = 3 if mine > theirs else 0
                    teams[me]['journees'].append({'journee': ri + 1, 'opponent': names[other], 'played_games': 14, 'doubles': 2 if win else 0,
                                                  'match_score': 28 if win else 14, 'opp_score': 14 if win else 28, 'players': players(mine, win)})
                    teams[me]['journees'].append({'journee': ri + 4, 'opponent': names[other], 'match_score': None, 'opp_score': None, 'players': []})
        site = {'built': 'x', 'season': '2026/2027', 'DATA': {'M9': {'pool': 'D92_D1 Messieurs_Ph1 Poule 4', 'level': 'D1', 'teams': teams}},
                'STANDINGS': {'M9': [{'name': n, 'pos': i + 1, 'pts': [9, 7, 5, 3][i]} for i, n in enumerate(names)]}}
        with tempfile.TemporaryDirectory() as tmp:
            sp, op = Path(tmp) / 'site.json', Path(tmp) / 'out.json'
            sp.write_text(json.dumps(site))
            doc = fdp.main(sp, op, nsim=300, seed=1)
            self.assertTrue(op.exists())
        T = doc['teams']['M9']
        by = {t['name']: t for t in T['teams']}
        self.assertGreater(by['FORT 1']['pUp'], 0.9)
        self.assertGreater(by['FAIBLE 1']['pDown'], 0.9)
        self.assertEqual(T['objectif'], 'maintien')
        self.assertEqual(len(T['remaining']), 6)
        for m in T['remaining']:
            self.assertAlmostEqual(sum(m['p'].values()), 1.0, places=3)
        mine = [m for m in T['remaining'] if 'BOULOGNE' in m['a'] + m['b']]
        self.assertTrue(all('impact' in m for m in mine))


if __name__ == '__main__':
    unittest.main()
