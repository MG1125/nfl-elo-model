#!/usr/bin/env python
# coding: utf-8

# In[1]:


# =====================================
# NFL Elo Tuning & Prediction with Force Option
# =====================================

# ----------- USER SETTINGS -----------
SEASONS = range(2010, 2024)        # Historical seasons to load
VALIDATION_SEASON = 2023           # Season for tuning validation
N_TRIALS = 50                      # Number of Optuna tuning trials
HOME_TEAM = "PHI"                   # For prediction example
AWAY_TEAM = "DAL"                   # For prediction example
FORCE_REFRESH = False               # Set True to force re-tuning
# =====================================

import pandas as pd
import numpy as np
import random
import os
import optuna
import importlib.util
import io
import requests
import certifi

INITIAL_RATING = 1500
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

# -------------------------
# Elo functions
# -------------------------
def elo_expected(Ra, Rb, H=0):
    return 1.0 / (1.0 + 10 ** ((Rb - (Ra + H)) / 400))

def run_elo_over_games(games, K, H, p_add, p_exp, d_base, d_slope, return_all=False):
    ratings = {}
    predictions = []
    for _, row in games.iterrows():
        home, away = row["home_team"], row["away_team"]
        pts_home, pts_away = row["home_score"], row["away_score"]

        RA = ratings.get(home, INITIAL_RATING)
        RB = ratings.get(away, INITIAL_RATING)

        expected_home = elo_expected(RA, RB, H)
        margin = pts_home - pts_away

        mov_mult = ((abs(margin) + p_add) ** p_exp) / (d_base + d_slope * abs(RA - RB))
        S_home = 1.0 if margin > 0 else 0.0 if margin < 0 else 0.5
        change = K * mov_mult * (S_home - expected_home)

        ratings[home] = RA + change
        ratings[away] = RB - change
        predictions.append(expected_home)

    if return_all:
        return predictions, games, ratings
    return predictions

# -------------------------
# Data loading
# -------------------------
def load_games(seasons):
    frames = []
    for season in seasons:
        url = (
            f"https://github.com/nflverse/nflverse-data/releases/download/pbp/"
            f"play_by_play_{season}.csv.gz"
        )
        try:
            env_cert = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
            ca_bundle = env_cert if (env_cert and os.path.exists(env_cert)) else certifi.where()
            resp = requests.get(
                url,
                timeout=60,
                verify=ca_bundle,
                allow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; EloModel/1.0)"},
            )
            resp.raise_for_status()
            df = pd.read_csv(io.BytesIO(resp.content), compression="gzip", low_memory=False)
        except Exception:
            continue

        df = df[df["season_type"] == "REG"]
        frames.append(df[['season', 'home_team', 'away_team', 'home_score', 'away_score']])

    if not frames:
        raise ValueError("No season data could be loaded. Check URL or season range.")
    return pd.concat(frames).reset_index(drop=True)

# -------------------------
# Objective for Optuna
# -------------------------
def make_objective(train_games, val_games):
    def objective(trial):
        K = trial.suggest_float("K", 10, 40)
        H = trial.suggest_float("H", 20, 80)
        p_add = trial.suggest_float("p_add", 0.0, 2.0)
        p_exp = trial.suggest_float("p_exp", 0.5, 1.5)
        d_base = trial.suggest_float("d_base", 400, 1200)
        d_slope = trial.suggest_float("d_slope", 0.0, 3.0)

        ratings = {}
        for _, row in train_games.iterrows():
            home, away = row["home_team"], row["away_team"]
            pts_home, pts_away = row["home_score"], row["away_score"]

            RA = ratings.get(home, INITIAL_RATING)
            RB = ratings.get(away, INITIAL_RATING)
            expected_home = elo_expected(RA, RB, H)
            margin = pts_home - pts_away
            mov_mult = ((abs(margin) + p_add) ** p_exp) / (d_base + d_slope * abs(RA - RB))
            S_home = 1.0 if margin > 0 else 0.0 if margin < 0 else 0.5
            change = K * mov_mult * (S_home - expected_home)
            ratings[home] = RA + change
            ratings[away] = RB - change

        preds, outcomes = [], []
        for _, row in val_games.iterrows():
            home, away = row["home_team"], row["away_team"]
            RA = ratings.get(home, INITIAL_RATING)
            RB = ratings.get(away, INITIAL_RATING)
            preds.append(elo_expected(RA, RB, H))
            outcomes.append(1.0 if row["home_score"] > row["away_score"] else 0.0)

        preds = np.array(preds)
        outcomes = np.array(outcomes)
        return np.mean((preds - outcomes) ** 2)
    return objective

# -------------------------
# Tuning with optional force refresh
# -------------------------
PARAM_MODULE = "elo_params"
PARAM_FILE = f"{PARAM_MODULE}.py"

def run_tuning(seasons, validation_season, n_trials=50, force_refresh=False):
    if not force_refresh and os.path.exists(PARAM_FILE):
        spec = importlib.util.spec_from_file_location(PARAM_MODULE, PARAM_FILE)
        params_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(params_mod)
        print("Loaded existing parameters from .py module.")
        return params_mod.BEST_PARAMS

    games = load_games(seasons)
    train_games = games[games["season"] < validation_season]
    val_games = games[games["season"] == validation_season]

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=RANDOM_SEED))
    study.optimize(make_objective(train_games, val_games), n_trials=n_trials)

    best_params = study.best_trial.params

    with open(PARAM_FILE, "w") as f:
        f.write(f"BEST_PARAMS = {best_params}\n")

    print("Saved best parameters to .py module.")
    return best_params

# -------------------------
# Ratings & predictions
# -------------------------
def get_current_ratings(seasons, params):
    games = load_games(seasons)
    _, _, ratings = run_elo_over_games(
        games, params["K"], params["H"], params["p_add"], params["p_exp"], params["d_base"], params["d_slope"], return_all=True
    )
    return ratings

def predict_matchup(home, away, ratings, params, elo_to_points=25.0):
    spread = (ratings.get(home, INITIAL_RATING) + params["H"] - ratings.get(away, INITIAL_RATING)) / elo_to_points
    win_prob = elo_expected(ratings.get(home, INITIAL_RATING), ratings.get(away, INITIAL_RATING), params["H"])
    return spread, win_prob

# -------------------------
# Run pipeline (when executed directly)
# -------------------------
if __name__ == "__main__":
    best_params = run_tuning(SEASONS, VALIDATION_SEASON, N_TRIALS, force_refresh=FORCE_REFRESH)
    ratings = get_current_ratings(SEASONS, best_params)

    spread, win_prob = predict_matchup(HOME_TEAM, AWAY_TEAM, ratings, best_params)
    print(f"\nPredicted spread ({HOME_TEAM} home): {spread:.2f} points")
    print(f"Home win probability: {win_prob*100:.1f}%")

