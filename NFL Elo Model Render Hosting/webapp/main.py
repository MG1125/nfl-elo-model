#!/usr/bin/env python3
import os
import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, List, Literal, Optional

# Import the existing Elo model module located one directory up
import sys
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

import NFL_ELO_ADVANCED_myles_poissonadded as model

app = FastAPI(title="NFL Elo Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PredictRequest(BaseModel):
    home: str
    away: str


_cached_params: Optional[Dict] = None
_cached_ratings: Optional[Dict[str, float]] = None


def _load_or_tune(force: bool = False, quick: bool = False) -> Dict:
    global _cached_params, _cached_ratings

    # Quick mode per user memory: last 6 seasons, 15 trials
    if quick:
        seasons = range(max(model.SEASONS) - 5, max(model.SEASONS) + 1)
        n_trials = 15
    else:
        seasons = model.SEASONS
        n_trials = model.N_TRIALS

    params = model.run_tuning(seasons, model.VALIDATION_SEASON, n_trials=n_trials, force_refresh=force)
    ratings = model.get_current_ratings(seasons, params)
    _cached_params = params
    _cached_ratings = ratings
    return params


def _ensure_cached():
    global _cached_params, _cached_ratings
    if _cached_params is None or _cached_ratings is None:
        _load_or_tune(force=False, quick=False)


@app.on_event("startup")
def startup_event():
    # Lazy; do nothing to speed startup. Ratings will be built on first request.
    pass


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/teams")
def get_teams() -> List[str]:
    # Ensure ratings are ready so we can list observed teams
    _ensure_cached()
    return sorted(list(_cached_ratings.keys()))


@app.post("/predict")
def predict(req: PredictRequest):
    _ensure_cached()
    home = req.home.strip().upper()
    away = req.away.strip().upper()
    if home == away:
        raise HTTPException(status_code=400, detail="Home and away must be different teams")
    spread, win_prob = model.predict_matchup(home, away, _cached_ratings, _cached_params)
    return {
        "home": home,
        "away": away,
        "spread": spread,
        "home_win_prob": win_prob,
    }


def _retune_job(mode: Literal["quick", "full"], force: bool):
    quick = mode == "quick"
    _load_or_tune(force=force, quick=quick)


@app.post("/retune")
def retune(background_tasks: BackgroundTasks, mode: Literal["quick", "full"] = Query("quick"), force: bool = Query(False)):
    background_tasks.add_task(_retune_job, mode, force)
    return {"status": "retune_started", "mode": mode, "force": force}


# Serve frontend static files from ./static
static_dir = os.path.join(CURRENT_DIR, "static")
if not os.path.isdir(static_dir):
    os.makedirs(static_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)


