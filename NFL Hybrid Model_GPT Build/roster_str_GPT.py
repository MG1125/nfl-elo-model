import os
import pandas as pd
import nfl_data_py as nfl
from typing import Dict, Optional, Tuple
from urllib.error import HTTPError, URLError
from typing import List

# ---------------------------
# Config / Constants
# ---------------------------

CACHE_DIR = ".nfl_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

POSITION_GROUPS = {
    "QB": ["QB"],
    "Skill": ["WR", "RB", "TE"],
    "OL": ["LT", "LG", "C", "RG", "RT", "OL"],
    "Front7": ["DL", "DE", "DT", "LB", "EDGE"],
    "Secondary": ["CB", "S", "FS", "SS"],
}

DEFAULT_WEIGHTS = {
    "QB": 0.40,
    "Skill": 0.20,
    "OL": 0.15,
    "Front7": 0.15,
    "Secondary": 0.10,
}

DEPTH_CHART_MULTIPLIER = {
    "starter": 1.0,
    "backup": 0.5,
    "third": 0.25,
    "practice": 0.1,
}

# Current NFL team codes (32 teams)
NFL_TEAMS: List[str] = [
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
    "DAL", "DEN", "DET", "GB",  "HOU", "IND", "JAX", "KC",
    "LAC", "LAR", "LV",  "MIA", "MIN", "NE",  "NO",  "NYG",
    "NYJ", "PHI", "PIT", "SEA", "SF",  "TB",  "TEN", "WAS",
]

# ---------------------------
# Helper: Cache Layer
# ---------------------------

def cached_weekly_roster(season: int, week: int) -> pd.DataFrame:
    """
    Load a weekly roster from cache if it exists; otherwise fetch, filter, and cache it.
    """
    filename = f"roster_{season}_w{week:02d}.csv"
    cache_path = os.path.join(CACHE_DIR, filename)
    if os.path.exists(cache_path):
        return pd.read_csv(cache_path)

    # Fetch data using nfl_data_py for the season, then filter by week before caching
    try:
        roster_all_weeks = nfl.import_weekly_rosters([season])
    except (HTTPError, URLError):
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()
    if "week" in roster_all_weeks.columns:
        roster_week = roster_all_weeks[roster_all_weeks["week"] == week]
    else:
        # If no explicit week column, fall back to saving the full season (best-effort)
        roster_week = roster_all_weeks

    roster_week.to_csv(cache_path, index=False)
    return roster_week

# ---------------------------
# Data Fetching
# ---------------------------

def fetch_team_data(team_code: str, season: int, week: int) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Fetch roster, injuries, and snap counts for a given team, season & week.
    """
    roster_df = cached_weekly_roster(season, week)
    if "team" in roster_df.columns:
        roster_df = roster_df[roster_df["team"] == team_code]
    if "week" in roster_df.columns:
        roster_df = roster_df[roster_df["week"] == week]

    try:
        injuries_df = nfl.import_injuries([season])
    except (HTTPError, URLError):
        injuries_df = pd.DataFrame()
    except Exception:
        injuries_df = pd.DataFrame()
    if not injuries_df.empty:
        injuries_df = injuries_df[(injuries_df["team"] == team_code) & (injuries_df["week"] == week)]

    try:
        snaps_df = nfl.import_snap_counts([season])
    except (HTTPError, URLError):
        snaps_df = pd.DataFrame()
    except Exception:
        snaps_df = pd.DataFrame()
    if not snaps_df.empty:
        snaps_df = snaps_df[snaps_df["team"] == team_code]
        if "week" in snaps_df.columns:
            snaps_df = snaps_df[snaps_df["week"] == week]

    return roster_df, injuries_df, snaps_df

# ---------------------------
# Strength Computation
# ---------------------------

def get_roster_strength(
    roster_df: pd.DataFrame,
    injuries_df: pd.DataFrame,
    snaps_df: pd.DataFrame,
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Compute roster strength given roster, injuries, and snaps.
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    injuries_status = {}
    for _, row in injuries_df.iterrows():
        name_key = row.get("full_name") or row.get("player") or row.get("name")
        status_val = row.get("report_status") or row.get("status") or ""
        if name_key:
            injuries_status[name_key] = str(status_val).lower()

    total_strength = 0.0

    for _, row in roster_df.iterrows():
        name = (
            row.get("full_name")
            or row.get("player")
            or row.get("player_name")
            or row.get("name")
        )
        pos = row.get("position")
        depth = row.get("depth_chart_position", "starter").lower()

        if not name or not pos:
            continue

        # Skip if fully out
        if name in injuries_status and injuries_status[name] == "out":
            continue

        # Adjust for questionable/doubtful
        injury_multiplier = 1.0
        if name in injuries_status and injuries_status[name] in ("questionable", "doubtful"):
            injury_multiplier = 0.5

        # Depth chart multiplier
        depth_mult = DEPTH_CHART_MULTIPLIER.get(depth, 0.5)

        # Snap percentage multiplier
        snap_mult = 1.0
        if not snaps_df.empty:
            snap_row = snaps_df[
                snaps_df.get("player", pd.Series(index=snaps_df.index, dtype=object)).fillna("") == name
            ]
            if snap_row.empty and "full_name" in snaps_df.columns:
                snap_row = snaps_df[snaps_df["full_name"] == name]
            if not snap_row.empty:
                snap_pct = (
                    snap_row.iloc[0].get("offense_pct")
                    or snap_row.iloc[0].get("defense_pct")
                    or snap_row.iloc[0].get("special_teams_pct")
                )
                if pd.notna(snap_pct):
                    try:
                        snap_mult = float(snap_pct) / 100.0
                    except (TypeError, ValueError):
                        pass

        # Position group
        group = None
        for g, positions in POSITION_GROUPS.items():
            if pos in positions:
                group = g
                break
        if not group:
            continue

        group_weight = weights.get(group, 0.0)
        contribution = group_weight * depth_mult * injury_multiplier * snap_mult
        total_strength += contribution

    return total_strength

# ---------------------------
# Normalization and League Aggregation
# ---------------------------

def min_max_normalize(values: List[float]) -> List[float]:
    if not values:
        return []
    vmin = min(values)
    vmax = max(values)
    if vmax == vmin:
        return [0.0 for _ in values]
    return [(v - vmin) / (vmax - vmin) for v in values]


def compute_team_strength(team_code: str, season: int, week: int) -> float:
    roster, injuries, snaps = fetch_team_data(team_code, season, week)
    return get_roster_strength(roster, injuries, snaps)


def compute_league_strengths(season: int, week: int) -> Dict[str, float]:
    results: Dict[str, float] = {}
    for code in NFL_TEAMS:
        try:
            results[code] = compute_team_strength(code, season, week)
        except Exception:
            results[code] = 0.0
    return results


def z_score_normalize(values: List[float]) -> List[float]:
    if not values:
        return []
    mean_val = sum(values) / len(values)
    # Population standard deviation for league-wide comparison
    var = sum((v - mean_val) ** 2 for v in values) / len(values)
    std = var ** 0.5
    if std == 0:
        return [0.0 for _ in values]
    return [(v - mean_val) / std for v in values]

# ---------------------------
# Demo
# ---------------------------

if __name__ == "__main__":
    # Configure matchup
    home_team = "BAL"
    away_team = "CLE"
    season = 2025
    week = 1

    print(f"Matchup: Home={home_team}, Away={away_team}")

    # Compute raw strengths
    league = compute_league_strengths(season, week)
    values = [league[t] for t in NFL_TEAMS]
    mm_vals = min_max_normalize(values)
    z_vals = z_score_normalize(values)
    team_to_minmax = {team: val for team, val in zip(NFL_TEAMS, mm_vals)}
    team_to_z = {team: val for team, val in zip(NFL_TEAMS, z_vals)}

    # Ensure fresh computation for the two teams in case of cache timing
    home_raw = compute_team_strength(home_team, season, week)
    away_raw = compute_team_strength(away_team, season, week)
    home_mm = team_to_minmax.get(home_team, 0.0)
    away_mm = team_to_minmax.get(away_team, 0.0)
    home_z = team_to_z.get(home_team, 0.0)
    away_z = team_to_z.get(away_team, 0.0)

    print(f"{home_team} strength — raw: {home_raw:.3f}, min-max: {home_mm:.3f}, z-score: {home_z:.3f}")
    print(f"{away_team} strength — raw: {away_raw:.3f}, min-max: {away_mm:.3f}, z-score: {away_z:.3f}")
