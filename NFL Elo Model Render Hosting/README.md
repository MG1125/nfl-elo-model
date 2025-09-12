# NFL Elo Model Web App

A web application for NFL game predictions using Elo ratings with tuning capabilities.

## Files Included

- `NFL_ELO_ADVANCED_myles_poissonadded.py` - The core Elo model
- `webapp/main.py` - FastAPI backend server
- `webapp/static/` - Frontend files (HTML, CSS, JS)
- `requirements.txt` - Python dependencies
- `render.yaml` - Render deployment configuration
- `Procfile` - Alternative deployment file
- `runtime.txt` - Python version specification
- `.gitignore` - Git ignore rules
- `README.md` - This file

## Quick Start (Local)

1. **Create and activate virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the server:**
   ```bash
   python webapp/main.py
   ```

4. **Open in browser:**
   Go to `http://localhost:8000`

## Deploy to Render (Free)

1. **Push to GitHub:**
   - Create a new repository on GitHub
   - Upload all files from this folder
   - Push to GitHub

2. **Deploy on Render:**
   - Go to [render.com](https://render.com)
   - Sign up/login with GitHub
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Use these settings:
     - **Build Command:** `pip install -r requirements.txt`
     - **Start Command:** `python webapp/main.py`
     - **Python Version:** 3.10.12
   - Click "Create Web Service"

3. **Your app will be live** at `https://your-app-name.onrender.com`

## Features

- **Predictions**: Enter home and away team codes to get win probability and point spread
- **Quick Retune**: Fast retuning with 15 trials over last 6 seasons
- **Full Retune**: Complete retuning with 50 trials over all seasons (2010-2024)
- **Team Codes**: Use 3-letter NFL team abbreviations (PHI, DAL, KC, etc.)

## Usage

1. Enter team codes in the text fields (e.g., "PHI" for Philadelphia, "DAL" for Dallas)
2. Click "Predict" to get the prediction
3. Use "Quick Retune" for faster updates or "Full Retune" for comprehensive retraining
4. Check the "Available Teams" section to see all valid team codes

## API Endpoints

- `GET /health` - Health check
- `GET /teams` - List all available teams
- `POST /predict` - Make a prediction
- `POST /retune?mode=quick|full` - Start retuning

## Notes

- First startup may take 30-60 seconds to download data and perform initial tuning
- Retuning runs in the background - you can continue making predictions
- The model uses historical NFL data from 2010-2024
- Render free tier may have cold starts (first request after idle time takes longer)