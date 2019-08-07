import pulp
from pulp import *
from pulp.solvers import CPLEX_PY
from pydfs_lineup_optimizer import get_optimizer, Site, Sport, CSVLineupExporter
from pydfs_lineup_optimizer.solvers.pulp_solver import PuLPSolver
class CustomPuLPSolver(PuLPSolver):
    LP_SOLVER = pulp.CPLEX_PY(msg=0)

optimizer = get_optimizer(Site.DRAFTKINGS, Sport.BASEBALL, solver=CustomPuLPSolver)

optimizer.load_players_from_csv("BBM_DK.csv")

for player in optimizer.players:
    if player.efficiency == 0:
        optimizer.remove_player(player)
optimizer.set_team_stacking([5])
optimizer.set_max_repeating_players(7)
optimizer.set_min_salary_cap(49000)
optimizer.restrict_positions_for_opposing_team(['SP'], ['1B', '2B', '3B', 'SS', 'OF', 'C', 'SP', 'RP'])

for lineup in optimizer.optimize(n=1000):
    print(lineup.players, lineup.fantasy_points_projection)  # list of players