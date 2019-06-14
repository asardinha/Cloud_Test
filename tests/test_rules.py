from __future__ import absolute_import, division
import unittest
from copy import deepcopy
from collections import Counter
from datetime import datetime
from math import ceil
from pydfs_lineup_optimizer import get_optimizer
from pydfs_lineup_optimizer.constants import Site, Sport
from pydfs_lineup_optimizer.player import Player, GameInfo
from pydfs_lineup_optimizer.exceptions import LineupOptimizerException
from pydfs_lineup_optimizer.rules import ProjectedOwnershipRule
from pydfs_lineup_optimizer.utils import list_intersection
from .utils import create_players, load_players, count_players_in_lineups


class OptimizerRulesTestCase(unittest.TestCase):
    def setUp(self):
        self.players = load_players()
        self.lineup_optimizer = get_optimizer(Site.DRAFTKINGS, Sport.BASKETBALL)
        self.lineup_optimizer.load_players(self.players)

    def test_with_injured_optimize(self):
        optimizer = self.lineup_optimizer
        cool_player = Player('1', 'P1', 'P1', ['PG'], 'team1', 1, 200, is_injured=True)
        optimizer.extend_players([cool_player])
        lineup = next(optimizer.optimize(1))
        self.assertNotIn(cool_player, lineup)
        lineup = next(optimizer.optimize(1, with_injured=True))
        self.assertIn(cool_player, lineup)

    def test_unique_player_rule(self):
        optimizer = get_optimizer(Site.DRAFTKINGS, Sport.GOLF)
        players = create_players(['G'] * 10)
        high_fppg_player = Player('1', 'High FPPG', 'Player', ['G'], '', 50, 200)
        players.extend([high_fppg_player] * 2)
        optimizer.load_players(players)
        lineup = next(optimizer.optimize(1))
        self.assertEqual(len([p for p in lineup if p == high_fppg_player]), 1)

    def test_randomness(self):
        optimized_lineup = next(self.lineup_optimizer.optimize(1))
        random_lineup = next(self.lineup_optimizer.optimize(1, randomness=True))
        self.assertTrue(optimized_lineup.fantasy_points_projection >= random_lineup.fantasy_points_projection)
        self.assertTrue(
            random_lineup.fantasy_points_projection >
            (1 - self.lineup_optimizer._max_deviation) * optimized_lineup.fantasy_points_projection
        )

    def test_lineup_with_players_from_same_positions(self):
        self.lineup_optimizer.load_players(create_players(['PG', 'SG', 'SF', 'PF', 'C', 'PG', 'SF', 'PF']))
        self.lineup_optimizer.extend_players([
            Player('1', 'p1', 'p1', ['C'], 'DEN', 1000, 2),  # Shouldn't be in lineup because of small efficiency
        ])
        self.lineup_optimizer.set_players_with_same_position({'C': 1})
        lineup = next(self.lineup_optimizer.optimize(1))
        self.assertTrue(len(list(filter(lambda x: 'C' in x.positions, lineup.lineup))) >= 2)

    def test_lineup_with_players_from_same_team(self):
        teams = {'CAVS': 4, 'LAC': 4}
        self.lineup_optimizer.set_players_from_one_team(teams)
        lineup = next(self.lineup_optimizer.optimize(1))
        for team, total in teams.items():
            self.assertEqual(len(list(filter(lambda x: x.team == team, lineup.lineup))), total)


class TestNotRepeatingPlayerTestCase(unittest.TestCase):
    def setUp(self):
        self.players = load_players()
        self.high_fppg_players = create_players(['PG', 'SG', 'SF', 'PF', 'C', 'PG', 'SF'], fppg=1000)
        self.lineup_optimizer = get_optimizer(Site.DRAFTKINGS, Sport.BASKETBALL)
        self.lineup_optimizer.load_players(self.players + self.high_fppg_players)

    def test_not_repeating_players(self):
        total_lineups = 3
        self.lineup_optimizer.set_max_repeating_players(3)
        custom_players_in_lineup = []
        for lineup in self.lineup_optimizer.optimize(total_lineups):
            custom_players_in_lineup.append(sum(1 for player in lineup if player in self.high_fppg_players))
        self.assertListEqual(custom_players_in_lineup, [7] + [3] * (total_lineups - 1))

    def test_set_max_repeating_players_to_lineup_capacity(self):
        with self.assertRaises(LineupOptimizerException):
            self.lineup_optimizer.set_max_repeating_players(self.lineup_optimizer.settings.get_total_players())

    def test_set_max_repeating_players_to_zero(self):
        with self.assertRaises(LineupOptimizerException):
            self.lineup_optimizer.set_max_repeating_players(0)


class TestMinSalaryCapTestCase(unittest.TestCase):
    def setUp(self):
        self.small_salary_player = Player('1', 'p1', 'p1', ['PG'], 'team1', 1, 200)
        self.players = load_players()
        self.players.append(self.small_salary_player)
        self.lineup_optimizer = get_optimizer(Site.DRAFTKINGS, Sport.BASKETBALL)
        self.lineup_optimizer.load_players(self.players)
        self.min_salary_cap = self.lineup_optimizer.settings.budget

    def test_min_salary_cap(self):
        self.lineup_optimizer.set_min_salary_cap(self.min_salary_cap)
        lineup = next(self.lineup_optimizer.optimize(1))
        self.assertEqual(lineup.salary_costs, self.min_salary_cap)
        self.assertNotIn(self.small_salary_player, lineup)

    def test_lock_player_that_break_min_salary_cap_constraint(self):
        self.lineup_optimizer.set_min_salary_cap(self.min_salary_cap)
        with self.assertRaises(LineupOptimizerException):
            self.lineup_optimizer.add_player_to_lineup(self.small_salary_player)
            next(self.lineup_optimizer.optimize(1))

    def test_set_min_salary_greater_than_max_budget(self):
        with self.assertRaises(LineupOptimizerException):
            self.lineup_optimizer.set_min_salary_cap(self.min_salary_cap * 2)


class TestPositionsFromSameTeamTestCase(unittest.TestCase):
    def setUp(self):
        self.optimizer = get_optimizer(Site.YAHOO, Sport.BASKETBALL)
        self.same_team = 'TEST'
        self.players = [
            Player('1', 'p1', 'p1', ['PG'], self.same_team, 10, 200),
            Player('2', 'p2', 'p2', ['SG'], 'team2', 10, 200),
            Player('3', 'p3', 'p3', ['SF'], 'team3', 10, 200),
            Player('4', 'p4', 'p4', ['PF'], 'team4', 10, 200),
            Player('5', 'p5', 'p5', ['C'], 'team5', 10, 200),
            Player('6', 'p6', 'p6', ['PG', 'SG'], 'team6', 10, 200),
            Player('7', 'p7', 'p7', ['SF', 'PF'], 'team7', 10, 200),
            Player('8', 'p8', 'p8', ['PG', 'SG', 'SF'], 'team8', 10, 200),
            Player('9', 'p9', 'p9', ['C'], self.same_team, 10, 5),
            Player('10', 'p10', 'p10', ['SF'], self.same_team, 10, 2),
            Player('11', 'p11', 'p11', ['PF', 'C'], self.same_team, 10, 2),
        ]
        self.optimizer.load_players(self.players)

    def test_positions_from_same_team(self):
        combinations = [['PG', 'C'], ['PG', 'SF', 'C'], ['PG', 'SF', 'C', 'C']]
        for combination in combinations:
            self.optimizer.set_positions_for_same_team(combination)
            lineup = next(self.optimizer.optimize(1))
            self.assertEqual(len([p for p in lineup.lineup if p.team == self.same_team]), len(combination))

    def test_reset_positions_from_same_team(self):
        self.optimizer.set_positions_for_same_team(['PG', 'C'])
        self.optimizer.set_positions_for_same_team(None)
        lineup = next(self.optimizer.optimize(1))
        self.assertEqual(len(set([p.team for p in lineup.lineup])), 8)


class TestMaxFromOneTeamTestCase(unittest.TestCase):
    def setUp(self):
        self.max_from_one_team = 1
        self.test_team = 'TEST'
        self.players = load_players()
        self.effective_players = create_players(['PG/SG', 'SF/PF', 'C'], salary=10, fppg=200, team=self.test_team)
        self.lineup_optimizer = get_optimizer(Site.DRAFTKINGS, Sport.BASKETBALL)
        self.lineup_optimizer.settings.max_from_one_team = self.max_from_one_team
        self.lineup_optimizer.load_players(self.players + self.effective_players)

    def test_max_from_one_team(self):
        lineup = next(self.lineup_optimizer.optimize(1))
        team_counter = Counter([p.team for p in lineup.lineup])
        self.assertTrue(all([team_players <= self.max_from_one_team for team_players in team_counter.values()]))

    def test_set_player_from_one_team_greater_than_constraint(self):
        with self.assertRaises(LineupOptimizerException):
            self.lineup_optimizer.set_players_from_one_team({'DEN': 3})
            next(self.lineup_optimizer.optimize(1))

    def test_lock_players_from_same_team(self):
        self.lineup_optimizer.add_player_to_lineup(self.effective_players[0])
        with self.assertRaises(LineupOptimizerException):
            self.lineup_optimizer.add_player_to_lineup(self.effective_players[1])


class ExposureTestCase(unittest.TestCase):
    def setUp(self):
        self.players = load_players()
        self.player_with_max_exposure = [
            Player('1', 'p1', 'p1', ['PG', 'SG'], 'DEN', 10, 200, max_exposure=0.3),
            Player('2', 'p2', 'p2', ['PF', 'SF'], 'DEN', 10, 200),
            Player('3', 'p3', 'p3', ['C'], 'DEN', 100, 2, max_exposure=0.35),
            Player('4', 'p4', 'p4', ['PG'], 'DEN', 100, 2),
            Player('5', 'p5', 'p5', ['PF'], 'DEN', 100, 2, max_exposure=0),
            Player('6', 'p6', 'p6', ['SF'], 'DEN', 1, 2001, max_exposure=0),
        ]
        self.players_with_min_exposure = [
            Player('7', 'p7', 'p7', ['PG', 'SG'], 'SAS', 1000, 0, min_exposure=0.3),
            Player('8', 'p8', 'p8', ['C'], 'SAS', 1000, 0, min_exposure=0.35),
            Player('9', 'p9', 'p9', ['C'], 'SAS', 1000, 0, min_exposure=1),
        ]
        self.lineup_optimizer = get_optimizer(Site.DRAFTKINGS, Sport.BASKETBALL)
        self.lineup_optimizer.load_players(self.players)

    def test_max_exposure(self):
        max_exposure = 0.5
        optimizer = self.lineup_optimizer
        optimizer.extend_players(self.player_with_max_exposure)
        # This players should be in each lineup
        players = [player for player in self.player_with_max_exposure if player.efficiency > 1]
        lineups_with_players = count_players_in_lineups(players, optimizer.optimize(10, max_exposure=max_exposure))
        for player in players:
            if player.max_exposure is not None:
                self.assertEqual(lineups_with_players[player], ceil(player.max_exposure * 10))
            else:
                self.assertLessEqual(lineups_with_players[player], 5)

    def test_locked_players_max_exposure(self):
        max_exposure = 0.5
        optimizer = self.lineup_optimizer
        players = self.player_with_max_exposure
        optimizer.extend_players(players)
        locked_players = players[2:4]
        for player in locked_players:
            optimizer.add_player_to_lineup(player)
        lineups_with_players = count_players_in_lineups(locked_players,
                                                        optimizer.optimize(10, max_exposure=max_exposure))
        for player in locked_players:
            count_expected = ceil((player.max_exposure if player.max_exposure is not None else max_exposure) * 10)
            self.assertEqual(lineups_with_players[player], count_expected)

    def test_lock_player_with_zero_max_exposure(self):
        self.lineup_optimizer.extend_players(self.player_with_max_exposure)
        with self.assertRaises(LineupOptimizerException):
            self.lineup_optimizer.add_player_to_lineup(self.player_with_max_exposure[4])

    def test_min_exposure(self):
        optimizer = self.lineup_optimizer
        players = self.players_with_min_exposure
        optimizer.extend_players(players)
        lineups_with_players = count_players_in_lineups(players, optimizer.optimize(10))
        self.assertEqual(lineups_with_players[players[0]], 3)
        self.assertEqual(lineups_with_players[players[1]], 4)
        self.assertEqual(lineups_with_players[players[2]], 10)


class ProjectedOwnershipTestCase(unittest.TestCase):
    def setUp(self):
        self.players = [
            Player('1', 'Golf Player 1', '', ['G'], '', 5000, 200, projected_ownership=0.95),
            Player('2', 'Golf Player 2', '', ['G'], '', 5000, 20, projected_ownership=0.7),
            Player('3', 'Golf Player 3', '', ['G'], '', 5000, 20, projected_ownership=0.7),
            Player('4', 'Golf Player 4', '', ['G'], '', 5000, 20, projected_ownership=0.7),
            Player('5', 'Golf Player 5', '', ['G'], '', 5000, 5, projected_ownership=0.5),
            Player('6', 'Golf Player 6', '', ['G'], '', 5000, 5, projected_ownership=0.5),
            Player('7', 'Golf Player 7', '', ['G'], '', 5000, 5, projected_ownership=0.5),
            Player('8', 'Golf Player 8', '', ['G'], '', 5000, 5, projected_ownership=0.5),
            Player('9', 'Golf Player 9', '', ['G'], '', 5000, 5, projected_ownership=0.5),
            Player('10', 'Golf Player 10', '', ['G'], '', 5000, 5, projected_ownership=0.5),
        ]
        self.optimizer = get_optimizer(Site.DRAFTKINGS, Sport.GOLF)
        self.optimizer.load_players(self.players)

    def test_min_projection_greater_than_max(self):
        with self.assertRaises(LineupOptimizerException):
            self.optimizer.set_projected_ownership(1, 0.5)

    def test_clear_projected_ownership_rule(self):
        self.optimizer.set_projected_ownership(0.5, 1)
        self.optimizer.set_projected_ownership()  # Should remove rule
        with self.assertRaises(LineupOptimizerException):
            self.optimizer.remove_rule(ProjectedOwnershipRule, silent=False)

    def test_min_projected_ownership_constraint(self):
        min_projected_ownership = 0.6
        self.optimizer.set_projected_ownership(min_projected_ownership=min_projected_ownership)
        lineup = next(self.optimizer.optimize(n=1))
        self.assertGreaterEqual(sum([p.projected_ownership for p in lineup.players]) / len(lineup.players),
                                min_projected_ownership)

    def test_max_projected_ownership_constraint(self):
        max_projected_ownership = 0.6
        self.optimizer.set_projected_ownership(max_projected_ownership=max_projected_ownership)
        lineup = next(self.optimizer.optimize(n=1))
        self.assertLessEqual(sum([p.projected_ownership for p in lineup.players]) / len(lineup.players),
                             max_projected_ownership)

    def test_both_projected_ownership_constraint(self):
        min_projected_ownership = 0.49
        max_projected_ownership = 0.51
        self.optimizer.set_projected_ownership(min_projected_ownership, max_projected_ownership)
        lineup = next(self.optimizer.optimize(n=1))
        self.assertTrue(all([p.projected_ownership == 0.5 for p in lineup.players]))

    def test_projected_ownership_for_locked_players(self):
        max_projected_ownership = 0.59  # ownership for generating best player and 5 worst players
        self.optimizer.add_player_to_lineup(self.players[1])
        self.optimizer.set_projected_ownership(max_projected_ownership=max_projected_ownership)
        lineup = next(self.optimizer.optimize(n=1))
        self.assertTrue(self.players[0] not in lineup.players)

    def test_projected_ownership_constraint_for_user_without_ownership(self):
        optimizer = get_optimizer(Site.DRAFTKINGS, Sport.GOLF)
        players = deepcopy(self.players)
        for player in players[1:]:
            player.projected_ownership = None
        optimizer.load_players(players)
        optimizer.set_projected_ownership(max_projected_ownership=0.9)
        lineup = next(optimizer.optimize(n=1))
        self.assertTrue(self.players[0] not in lineup.players)


class StacksRuleTestCase(unittest.TestCase):
    def setUp(self):
        self.players = load_players()
        self.optimizer = get_optimizer(Site.DRAFTKINGS, Sport.BASKETBALL)
        self.optimizer.settings.max_from_one_team = 4
        self.optimizer.load_players(self.players)

    def test_stacks_correctness(self):
        stacks = [4, 2]
        self.optimizer.set_team_stacking(stacks)
        self.optimizer.set_positions_for_same_team(['PG', 'SG', 'SF', 'PF'])
        lineup = next(self.optimizer.optimize(n=1))
        teams = Counter([player.team for player in lineup])
        self.assertListEqual(stacks, [stack[1] for stack in Counter(teams).most_common(len(stacks))])

    def test_stacks_greater_than_total_players(self):
        stacks = [3, 3, 3]
        with self.assertRaises(LineupOptimizerException):
            self.optimizer.set_team_stacking(stacks)

    def test_stack_greater_than_max_from_one_team(self):
        stacks = [5]
        with self.assertRaises(LineupOptimizerException):
            self.optimizer.set_team_stacking(stacks)


class PositionsForOpposingTeamTestCase(unittest.TestCase):
    def setUp(self):
        first_game_info = GameInfo('HOU', 'BOS', datetime.now(), False)
        second_game_info = GameInfo('CHI', 'NY', datetime.now(), False)
        self.players = [
            Player('1', '1', '1', ['SP', 'RP'], 'HOU', 3000, 15, game_info=first_game_info),
            Player('2', '2', '2', ['SP', 'RP'], 'BOS', 3000, 15, game_info=first_game_info),
            Player('3', '3', '3', ['C'], 'HOU', 3000, 15, game_info=first_game_info),
            Player('4', '4', '4', ['1B'], 'BOS', 3000, 15, game_info=first_game_info),
            Player('5', '5', '5', ['2B'], 'HOU', 3000, 15, game_info=first_game_info),
            Player('6', '6', '6', ['3B'], 'BOS', 3000, 15, game_info=first_game_info),
            Player('7', '7', '7', ['SS'], 'HOU', 3000, 15, game_info=first_game_info),
            Player('8', '8', '8', ['OF'], 'BOS', 3000, 15, game_info=first_game_info),
            Player('9', '9', '9', ['OF'], 'HOU', 3000, 15, game_info=first_game_info),
            Player('10', '10', '10', ['OF'], 'BOS', 3000, 15, game_info=first_game_info),
            Player('11', '11', '11', ['SP', 'RP'], 'CHI', 3000, 5, game_info=second_game_info),
            Player('12', '12', '12', ['SP', 'RP'], 'NY', 3000, 5, game_info=second_game_info),
        ]
        self.optimizer = get_optimizer(Site.DRAFTKINGS, Sport.BASEBALL)
        self.optimizer.load_players(self.players)

    def test_restrict_positions_for_opposing_team_correctness(self):
        first_team_positions = ['SP', 'RP']
        second_team_positions = ['1B', '2B', '3B']
        self.optimizer.restrict_positions_for_opposing_team(first_team_positions, second_team_positions)
        lineup = next(self.optimizer.optimize(1))
        pitcher_games = {player.game_info for player in lineup
                         if list_intersection(player.positions, first_team_positions)}
        hitters_games = {player.game_info for player in lineup
                         if list_intersection(player.positions, second_team_positions)}
        self.assertFalse(pitcher_games.intersection(hitters_games))

    def test_restrict_positions_if_game_not_specified(self):
        for player in self.players:
            player.game_info = None
        with self.assertRaises(LineupOptimizerException):
            self.optimizer.restrict_positions_for_opposing_team(['SP', 'RP'], ['1B'])


class RosterSpacingTestCase(unittest.TestCase):
    def setUp(self):
        self.players = [
            Player('1', '1', '1', ['SP', 'RP'], 'HOU', 3000, 15, ),
            Player('2', '2', '2', ['SP', 'RP'], 'HOU', 3000, 15, ),
            Player('3', '3', '3', ['C'], 'HOU', 3000, 15, ),
            Player('4', '4', '4', ['SS'], 'HOU', 3000, 15, ),
            Player('5', '5', '5', ['OF'], 'MIL', 3000, 15, ),
            Player('6', '6', '6', ['OF'], 'MIL', 3000, 15, ),
            Player('7', '7', '7', ['OF'], 'MIL', 3000, 15, ),
            Player('8', '8', '8', ['1B'], 'BOS', 3000, 15, roster_order=1),
            Player('9', '9', '9', ['2B'], 'BOS', 3000, 20, roster_order=2),
            Player('10', '10', '10', ['3B'], 'BOS', 3000, 25, roster_order=3),
            Player('11', '11', '11', ['1B'], 'NY', 3000, 30, roster_order=4),
            Player('12', '12', '12', ['2B'], 'NY', 3000, 35, roster_order=5),
            Player('13', '13', '13', ['3B'], 'NY', 3000, 40, roster_order=6),
        ]
        self.players_dict = {player.id: player for player in self.players}
        self.positions = ['1B', '2B', '3B']
        self.optimizer = get_optimizer(Site.DRAFTKINGS, Sport.BASEBALL)
        self.optimizer.load_players(self.players)

    def test_roster_spacing_correctness(self):
        self.optimizer.set_spacing_for_positions(self.positions, 2)
        lineup = next(self.optimizer.optimize(1))
        self.assertIn(self.players_dict['8'], lineup)
        self.assertIn(self.players_dict['12'], lineup)
        self.assertIn(self.players_dict['13'], lineup)
        self.optimizer.set_spacing_for_positions(self.positions, 3)
        lineup = next(self.optimizer.optimize(1))
        self.assertIn(self.players_dict['11'], lineup)
        self.assertIn(self.players_dict['12'], lineup)
        self.assertIn(self.players_dict['13'], lineup)

    def test_error_with_one_spacing_when_total_teams_not_enough(self):
        self.optimizer.set_spacing_for_positions(self.positions, 1)
        with self.assertRaises(LineupOptimizerException):
            next(self.optimizer.optimize(1))

    def test_passing_incorrect_positions(self):
        with self.assertRaises(LineupOptimizerException):
            self.optimizer.set_spacing_for_positions(['QB', 'WR'], 2)

    def test_passing_incorrect_spacing(self):
        with self.assertRaises(LineupOptimizerException):
            self.optimizer.set_spacing_for_positions(self.positions, 0)


class TestFanduelMaxFromOneTeamTestCase(unittest.TestCase):
    def setUp(self):
        self.players = [
            Player('1', '1', '1', ['P'], 'HOU', 3000, 10),
            Player('2', '2', '2', ['P'], 'NY', 3000, 20),
            Player('3', '3', '3', ['C'], 'BOS', 3000, 30),
            Player('4', '4', '4', ['SS'], 'HOU', 3000, 30),
            Player('5', '5', '5', ['OF'], 'HOU', 3000, 30),
            Player('6', '6', '6', ['OF'], 'HOU', 3000, 30),
            Player('7', '7', '7', ['OF'], 'HOU', 3000, 30),
            Player('8', '8', '8', ['1B'], 'HOU', 3000, 30),
            Player('9', '9', '9', ['2B'], 'MIA', 3000, 5),
            Player('10', '10', '10', ['3B'], 'ARI', 3000, 5),
            Player('11', '11', '11', ['1B'], 'ARI', 3000, 5),
        ]
        self.optimizer = get_optimizer(Site.FANDUEL, Sport.BASEBALL)
        self.optimizer.load_players(self.players)

    def test_max_hitters_from_one_team(self):
        lineup = next(self.optimizer.optimize(1))
        hou_players_positions = [player.lineup_position for player in lineup if player.team == 'HOU']
        self.assertEqual(len(hou_players_positions), 4)
        self.assertNotIn('P', hou_players_positions)

    def test_max_hitters_from_one_team_with_stacking(self):
        self.optimizer.set_team_stacking([5])
        lineup = next(self.optimizer.optimize(1))
        hou_players_positions = [player.lineup_position for player in lineup if player.team == 'HOU']
        self.assertEqual(len(hou_players_positions), 5)
        self.assertIn('P', hou_players_positions)
