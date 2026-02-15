"""
Prop Gem AI - Analyst Module (The Brain)
Uses OpenRouter + DeepSeek R1 for edge calculation
"""

import json
import os
from datetime import datetime, timedelta
import requests
from typing import Dict
from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    ANALYSIS_MODEL,
    APP_URL,
    RISK_MULTIPLIER,
    ANALYSIS_CACHE_MINUTES
)


ANALYST_INSTRUCTIONS = """
You are an expert NBA betting analyst. Analyze the player prop and return ONLY a JSON object.

Calculate edge as follows:
1. Implied Probability = 1 / Odds
2. Your Estimated Win Probability based on trends and matchup
3. Edge Percentage = Estimated Win % - Implied Probability

CRITICAL: Return edge_percentage as a DECIMAL (e.g., 0.10 for 10%, NOT 10.0).

Response format:
{
    "edge_percentage": 0.12,
    "rating": "SMASH",
    "confidence": "High",
    "reasoning": "brief explanation"
}

Rating rules:
- SMASH: edge >= 0.10 (10%+)
- LEAN: edge >= 0.03 and < 0.10 (3-9%)
- PASS: edge >= 0.00 and < 0.03 (0-2%)
- FADE: edge < 0.00 (negative edge)

Return ONLY valid JSON, no other text.
""".strip()


class PropAnalyst:
    """
    AI-powered edge analyst using DeepSeek R1 via OpenRouter
    Includes caching to reduce API costs
    """
    
    CACHE_FILE = "analysis_cache.json"

    def __init__(self):
        self.api_key = OPENROUTER_API_KEY
        self.base_url = OPENROUTER_BASE_URL
        self.model = ANALYSIS_MODEL
        self.referer = APP_URL
        self.enabled = self.api_key != "PLACEHOLDER" and bool(self.api_key)
    
    def _get_cache_key(self, player: str, stat: str, line: float, odds: float) -> str:
        """Generate unique cache key for a prop"""
        return f"{player}_{stat}_{line}_{odds:.2f}"
    
    def _load_cached_analysis(self, cache_key: str) -> Dict:
        """Load cached analysis if fresh (within ANALYSIS_CACHE_MINUTES)"""
        if not os.path.exists(self.CACHE_FILE):
            return {}
        
        try:
            with open(self.CACHE_FILE, 'r') as f:
                cache = json.load(f)
            
            if cache_key not in cache:
                return {}
            
            entry = cache[cache_key]
            cached_time = datetime.fromisoformat(entry.get('timestamp', '2000-01-01'))
            
            if datetime.now() - cached_time < timedelta(minutes=ANALYSIS_CACHE_MINUTES):
                return entry.get('data', {})
            return {}
        except Exception:
            return {}
    
    def _save_cached_analysis(self, cache_key: str, data: Dict):
        """Save analysis result to cache"""
        try:
            cache = {}
            if os.path.exists(self.CACHE_FILE):
                with open(self.CACHE_FILE, 'r') as f:
                    cache = json.load(f)
            
            cache[cache_key] = {
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            
            with open(self.CACHE_FILE, 'w') as f:
                json.dump(cache, f, indent=2)
        except Exception:
            pass  # Silent fail on cache write

    def _make_request(self, prompt: str) -> str:
        """Make API request to OpenRouter"""
        if not self.enabled:
            return ""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.referer
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": ANALYST_INSTRUCTIONS},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }

        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=90
            )
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content']
        except Exception as e:
            print(f"[ANALYSIS ERROR] {e}")
            return ""

    def _clean_json(self, text: str) -> str:
        """Extract JSON from response by finding first { and last }"""
        start = text.find('{')
        if start == -1:
            return "{}"

        end = text.rfind('}')
        if end == -1:
            return "{}"

        return text[start:end+1]

    def _parse_response(self, response: str) -> Dict:
        """Parse and validate the AI response"""
        if not response:
            return self._simulate_analysis()

        try:
            json_str = self._clean_json(response)
            data = json.loads(json_str)

            edge = data.get('edge_percentage', 0)

            # Handle if AI returned percentage instead of decimal
            if edge > 1:
                edge = edge / 100

            # Clamp to reasonable range
            edge = max(-0.2, min(0.3, edge))

            rating = data.get('rating', 'PASS')
            if rating not in ['SMASH', 'LEAN', 'PASS', 'FADE']:
                if edge >= 0.10:
                    rating = 'SMASH'
                elif edge >= 0.03:
                    rating = 'LEAN'
                elif edge >= 0.00:
                    rating = 'PASS'
                else:
                    rating = 'FADE'

            return {
                'edge_percentage': edge,
                'rating': rating,
                'confidence': data.get('confidence', 'Medium'),
                'reasoning': data.get('reasoning', 'No reasoning')
            }

        except json.JSONDecodeError:
            print(f"[PARSE ERROR] Could not parse response")
            return self._simulate_analysis()
        except Exception as e:
            print(f"[PARSE ERROR] {e}")
            return self._simulate_analysis()

    def analyze_prop(self, player: str, stat: str, line: float,
                     odds: float, trends: Dict, side: str = "Over") -> Dict:
        """
        Analyze a prop using DeepSeek AI (with 1-hour caching)

        Returns dict with:
        - edge_percentage: float (decimal, e.g., 0.05)
        - rating: str (SMASH/LEAN/PASS/FADE)
        - confidence: str
        - reasoning: str
        """
        # Check cache first
        cache_key = self._get_cache_key(player, stat, line, odds) + f"_{side}"
        cached = self._load_cached_analysis(cache_key)
        if cached:
            return cached
        
        if not self.enabled:
            return self._simulate_analysis()

        implied_prob = 1 / odds

        prompt = f"""Analyze this NBA player prop:

PLAYER: {player}
STAT: {stat}
LINE: {side.upper()} {line}
ODDS: {odds} (Implied: {implied_prob:.1%})

TREND DATA:
- Last 10 Hit Rate: {trends.get('last_10_hit_rate', 0):.0%}
- Trend: {trends.get('trend_direction', 'Unknown')}
- Injury Concern: {trends.get('has_injury_concern', False)}

Return ONLY the required JSON with edge_percentage as DECIMAL.
Keep reasoning concise - maximum 60 words."""

        response = self._make_request(prompt)
        result = self._parse_response(response)
        
        # Cache the result
        self._save_cached_analysis(cache_key, result)
        
        return result

    def _simulate_analysis(self) -> Dict:
        """Generate realistic simulated analysis"""
        import random

        edge = random.choice([0.12, 0.08, 0.05, 0.02, 0.01, -0.02, -0.05])

        if edge >= 0.10:
            rating = 'SMASH'
            confidence = 'High'
        elif edge >= 0.03:
            rating = 'LEAN'
            confidence = 'Medium'
        elif edge >= 0.00:
            rating = 'PASS'
            confidence = 'Low'
        else:
            rating = 'FADE'
            confidence = 'High'

        return {
            'edge_percentage': edge,
            'rating': rating,
            'confidence': confidence,
            'reasoning': 'Simulated analysis'
        }


def get_analysis(player: str, stat: str, line: float,
                 odds: float, trends: Dict) -> Dict:
    """
    Convenience function for getting AI analysis

    Returns dict with edge_percentage (decimal), rating, confidence
    """
    analyst = PropAnalyst()
    return analyst.analyze_prop(player, stat, line, odds, trends)
