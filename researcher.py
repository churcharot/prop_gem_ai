"""
Prop Gem AI - Researcher Module (The Eyes)
Uses OpenRouter + Perplexity Sonar for live trend research
"""

import requests
import json
import os
from datetime import datetime, timedelta
from typing import Dict
from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    RESEARCH_MODEL,
    APP_URL
)

TRENDS_CACHE_MINUTES = 60  # Cache trends for 1 hour


class TrendResearcher:
    """
    Live trend researcher using Perplexity Sonar via OpenRouter
    Gets Last 10 game hit rates, injury news, and matchup context
    Includes 1-hour caching to reduce API costs
    """
    
    CACHE_FILE = "trends_cache.json"

    def __init__(self):
        import config
        self.api_key = config.OPENROUTER_API_KEY  # Read at runtime so st.secrets override works
        self.base_url = OPENROUTER_BASE_URL
        self.model = RESEARCH_MODEL
        self.referer = APP_URL
        self.enabled = self.api_key != "PLACEHOLDER" and bool(self.api_key)
    
    def _get_cache_key(self, player: str, stat: str, line: float, side: str) -> str:
        """Generate unique cache key for trend lookup"""
        return f"{player}_{stat}_{side}_{line}"
    
    def _load_cached_trends(self, cache_key: str) -> Dict:
        """Load cached trends if still valid"""
        if not os.path.exists(self.CACHE_FILE):
            return None
        try:
            with open(self.CACHE_FILE, 'r') as f:
                cache = json.load(f)
            if cache_key in cache:
                entry = cache[cache_key]
                cached_time = datetime.fromisoformat(entry['timestamp'])
                if datetime.now() - cached_time < timedelta(minutes=TRENDS_CACHE_MINUTES):
                    return entry['data']
        except Exception:
            pass
        return None
    
    def _save_cached_trends(self, cache_key: str, data: Dict):
        """Save trends to cache"""
        cache = {}
        if os.path.exists(self.CACHE_FILE):
            try:
                with open(self.CACHE_FILE, 'r') as f:
                    cache = json.load(f)
            except Exception:
                pass
        cache[cache_key] = {
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        try:
            with open(self.CACHE_FILE, 'w') as f:
                json.dump(cache, f)
        except Exception:
            pass

    def _make_request(self, prompt: str):
        """Make API request to OpenRouter"""
        if not self.enabled:
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.referer
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}]
        }

        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content']
        except Exception as e:
            print(f"[RESEARCH ERROR] {e}")
            return None

    def get_player_trends(self, player: str, stat: str, line: float, side: str = "Over") -> Dict:
        """
        Research player trends: Last 10 hit rate, injuries, form
        Includes 1-hour caching
        """
        # Check cache first
        cache_key = self._get_cache_key(player, stat, line, side)
        cached = self._load_cached_trends(cache_key)
        if cached:
            return cached
        
        if not self.enabled:
            return self._simulate_trends(player, stat, line, side)

        prompt = f"""Search for {player}'s recent performance data for {side.upper()} {line} {stat}.

Provide:
1. Last 10 games hit rate (e.g., "7 out of 10")
2. Recent trend direction (Improving/Declining/Stable)
3. Any injuries or load management concerns
4. Matchup difficulty for {stat}

Be concise. Provide data points only."""

        response = self._make_request(prompt)

        if response:
            result = self._parse_trend_response(response, player, stat, line)
            self._save_cached_trends(cache_key, result)
            return result
        else:
            return self._simulate_trends(player, stat, line, side)

    def _parse_trend_response(self, response: str, player: str, stat: str, line: float) -> Dict:
        """Parse the trend response into structured data"""
        import re

        hit_rate_match = re.search(r'(\d+)\s*out\s*of\s*10', response, re.IGNORECASE)
        hit_rate_pct = re.search(r'(\d+)%', response)

        if hit_rate_match:
            hits = int(hit_rate_match.group(1))
            hit_rate = hits / 10
        elif hit_rate_pct:
            hit_rate = int(hit_rate_pct.group(1)) / 100
        else:
            hit_rate = 0.5

        trend_direction = "Stable"
        if any(word in response.lower() for word in ['improving', 'hot', 'up']):
            trend_direction = "Improving"
        elif any(word in response.lower() for word in ['declining', 'cold', 'down', 'struggling']):
            trend_direction = "Declining"

        has_injury = any(word in response.lower() for word in ['injury', 'injured', 'doubtful', 'out'])

        return {
            'player': player,
            'stat': stat,
            'line': line,
            'last_10_hit_rate': hit_rate,
            'trend_direction': trend_direction,
            'has_injury_concern': has_injury,
            'raw_notes': response[:300]
        }

    def _simulate_trends(self, player: str, stat: str, line: float, side: str = "Over") -> Dict:
        """Generate realistic simulated trends"""
        import random
        import hashlib

        hash_val = int(hashlib.md5(f"{player}_{stat}_{side}".encode()).hexdigest(), 16)
        random.seed(hash_val)

        hit_rate = random.choice([0.4, 0.5, 0.6, 0.7, 0.8])
        trend = random.choice(["Improving", "Stable", "Declining"])
        has_injury = random.random() < 0.15

        return {
            'player': player,
            'stat': stat,
            'line': line,
            'last_10_hit_rate': hit_rate,
            'trend_direction': trend,
            'has_injury_concern': has_injury,
            'raw_notes': f"Simulated: {int(hit_rate*10)}/10 {side} {line} {stat}"
        }


def get_player_trends(player: str, stat: str, line: float, side: str = "Over") -> Dict:
    """Convenience function for importing into main dashboard"""
    researcher = TrendResearcher()
    return researcher.get_player_trends(player, stat, line, side)
