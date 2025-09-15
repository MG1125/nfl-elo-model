NFL Team Strength Model
======================

This Python program computes NFL team roster strengths using weekly rosters,
injuries, and snap counts. It accounts for depth chart weighting, snap percentage,
and league-wide normalization. Data is fetched via the `nfl_data_py` library
and cached locally to minimize repeated downloads.

Features
--------

- Roster strength computation based on:
  - Player position groups
  - Depth chart role
  - Snap counts
  - Injuries

- Position Groups:
  QB         : QB
  Skill      : WR, RB, TE
  OL         : LT, LG, C, RG, RT, OL
  Front7     : DL, DE, DT, LB, EDGE
  Secondary  : CB, S, FS, SS

- Depth Chart Multipliers:
  starter : 1.0
  backup  : 0.5
  third   : 0.25
  practice: 0.1

- Snap Count Scaling: Player contributions scaled based on snap percentages.
- Injury Adjustment:
    - Out: excluded from strength
    - Questionable/Doubtful: contribution halved
- Local caching: Stores downloaded CSVs in `.nfl_cache/`
- League Normalization: Provides min-max and z-score normalized values.

Installation
------------

1. Clone the repository:
   git clone <your-repo-url>
   cd <your-repo>

2. Install dependencies:
   pip install pandas nfl_data_py

Usage
-----

Run the script to compute roster strengths and normalized values:

   python nfl_strength_model.py

This computes:
1. Raw roster strengths for all 32 NFL teams
2. Min-max normalized values (0-1)
3. Z-score normalized values (league mean/SD)
4. Prints sample matchup output (default PHI vs DAL, Week 1, 2025)

Example Output:

   Matchup: Home=PHI, Away=DAL
   PHI strength — raw: 1.235, min-max: 0.842, z-score: 0.765
   DAL strength — raw: 1.010, min-max: 0.643, z-score: -0.312

Configuration
-------------

- NFL Teams: Standard 32 team codes (ARI, ATL, BAL, …)
- Position Group Weights: DEFAULT_WEIGHTS in code
- Depth Chart Multipliers: DEPTH_CHART_MULTIPLIER
- Caching: `.nfl_cache/` folder stores downloaded CSVs

Functions
---------

- fetch_team_data(team_code, season, week) -> (roster_df, injuries_df, snaps_df)
- get_roster_strength(roster_df, injuries_df, snaps_df, weights) -> float
- compute_team_strength(team_code, season, week) -> float
- compute_league_strengths(season, week) -> dict of team_code: strength
- min_max_normalize(values) -> List[float]
- z_score_normalize(values) -> List[float]

Contribution Calculation
------------------------

Player Contribution:

          +--------------------+
          | Position Weight    |
          +--------------------+
                     |
                     v
          +--------------------+
          | Depth Chart Mult.  |
          +--------------------+
                     |
                     v
          +--------------------+
          | Snap % Multiplier  |
          +--------------------+
                     |
                     v
          +--------------------+
          | Injury Multiplier  |
          +--------------------+
                     |
                     v
        Sum of all players --> Team Strength

League Normalization:

    Raw Team Strengths
           |
           v
   +--------------------+       +--------------------+
   | Min-Max Normalized  |       | Z-Score Normalized |
   +--------------------+       +--------------------+
   0..1                        Std deviations from mean

Notes
-----

- Requires internet for first-time data download; cached files are reused.
- Handles missing or incomplete data gracefully.
- Designed to be agnostic of ELO or other matchup models.

License
-------

MIT License
