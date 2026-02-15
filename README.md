# 💎 Prop Gem AI

AI-Powered NBA Player Prop Edge Detection with line shopping across multiple sportsbooks.

## Features
- **Game Scanner** — Fetches live NBA props and analyzes edges using AI
- **Manual Analyzer** — Input any prop for instant AI analysis
- **Line Shopping** — Compares odds across DraftKings, Bet365, FanDuel, and more
- **Smart Ratings** — SMASH (≥10%), LEAN (3-9%), PASS (0-2%), FADE (<0%)

## 🚀 Deploy to Streamlit Cloud

### Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/prop_gem_ai.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy on Streamlit
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your GitHub account
3. Click **"New app"**
4. Select your repo, branch `main`, and file `app.py`
5. Click **Deploy**

### Step 3: Add Secrets
In the Streamlit Cloud dashboard, go to **Settings → Secrets** and paste:
```toml
ODDS_API_KEY = "your_odds_api_key_here"
OPENROUTER_API_KEY = "your_openrouter_api_key_here"
```

## 🔧 Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Add your keys to `.streamlit/secrets.toml`:
   ```toml
   ODDS_API_KEY = "your_key"
   OPENROUTER_API_KEY = "your_key"
   ```

3. Run:
   ```bash
   streamlit run app.py
   ```

## 🔒 Password
The app is password-protected. Default password: `gem2026`
