"""
Prop Gem AI - Configuration Settings
Production Version with OpenRouter

API keys are loaded from Streamlit secrets (Cloud dashboard or .streamlit/secrets.toml).
"""

# API Keys - loaded at runtime from st.secrets in app.py
ODDS_API_KEY = ""          # Set in Streamlit secrets: ODDS_API_KEY
OPENROUTER_API_KEY = ""    # Set in Streamlit secrets: OPENROUTER_API_KEY

# Risk Management
RISK_MULTIPLIER = 0.25  # 1/4 Kelly Criterion

# Edge Thresholds
SMASH_THRESHOLD = 0.10  # 10%+
LEAN_THRESHOLD = 0.03   # 3-9%
PASS_THRESHOLD = 0.00   # 0-2%
# Below 0% = FADE

# API Settings
NBA_SPORT_KEY = "basketball_nba"
ODDS_FORMAT = "decimal"
MARKETS = "player_points,player_rebounds,player_assists"
REGIONS = "us,eu,uk,us2"  # Global line shopping: US, Europe, UK, US2 (covers Bet365, Bovada, etc.)

# OpenRouter Settings
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
RESEARCH_MODEL = "perplexity/sonar"           # For live trend research
ANALYSIS_MODEL = "deepseek/deepseek-chat"     # DeepSeek V3 for edge calculation
APP_URL = "https://propgem.app"

# Cache Settings
CACHE_FILE = "nba_cache.json"
SCHEDULE_CACHE_MINUTES = 360  # 6 hours - schedule rarely changes
PROPS_CACHE_MINUTES = 15      # 15 min - lines change frequently
ANALYSIS_CACHE_MINUTES = 60   # 1 hour - save API costs on repeated analysis

# Threading
MAX_THREADS = 5  # Limit concurrent API calls to avoid rate limits

# Display
TABLE_MAX_WIDTH = 140
