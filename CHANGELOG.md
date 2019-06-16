# pydfs-lineup-optimizer Repository Change Log

All notable changes to this project will be documented in this file.

## [v2.5.1]
- Fixed optimization for roster spacing rule
- Fixed repeated lineups issue when optimizing in random mode

## [v2.5.0]
- Added lineup ordering rule
- Added DK NASCAR
- Added DK Tennis
- Added DK WNBA
- Added DK Captain Mode WNBA
- Added search by player id
- Added game info parsing for captain mode
- Fixed bug with total player for late-swap
- Fixed generating lineups with CPLEX solver
- Fixed game info parsing for individual sports
- Fixed minimum hitters FD rule
- Improved performance for sports without multi-positional players

## [v2.4.1]
- Fixed solver freezes on windows

## [v2.4.0]
- Added DK MLB captain mode
- Added teams stacking
- Added constraint for restricting players from opposing teams
- Fixed bug with duplicated positions in DK MLB late-swap
- Fixed default timezone for DK late-swap
- Improved performance for solver setup
- Added ability to change solver in PuLP

## [v2.3.0]
- Added DK late-swap
- Added DK MMA
- Fixed DK LOL settings
- Fixed FantasyDraft Golf settings
- Fixed DK captain mode settings

## [v2.2.1]
- Fixed import error for optimizer running on python 3.6

## [v2.2.0]
- Added DK captain mode
- Added minimum exposure
- Improved normal objective optimization
- Added DK template file format
- Fixed DK LOL settings

## [v2.1.0]
- Added projected ownership feature
- Added FanBall football
- Fixed FanDuel MLB max player from one team constraint

## [v2.0.3]
- Fixed FanDuel nfl settings

## [v2.0.2]
- Fixed FanDuel mlb settings

## [v2.0.0]
- Added custom constraints creation
- Optimized lineup generation speed
- Added max repeating players constraint
- Added new sports

## [v1.4.1]
- Changed settings for DraftKings

## [v1.4]
- Added min salary constraint.

## [v1.3]
- Fixed bug with setting lineup positions

## [v1.2]
- Added csv export
- Added constraints for positions in same team
- Changed constraint setting interface

