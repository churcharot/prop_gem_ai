"""
Prop Gem AI - Global Fetcher Module
Fetches NBA props from ALL regions (US, EU, UK, US2) for line shopping
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
import requests
from config import (
    ODDS_API_KEY, NBA_SPORT_KEY, MARKETS, REGIONS,
    ODDS_FORMAT, CACHE_FILE, SCHEDULE_CACHE_MINUTES, PROPS_CACHE_MINUTES
)


class OddsFetcher:
    """
    Global Odds Fetcher - collects lines from multiple regions
    for maximum line shopping opportunities
    """

    BASE_URL = "https://api.the-odds-api.com/v4/sports"

    def __init__(self):
        self.api_key = ODDS_API_KEY
        self.cache_file = CACHE_FILE

    def _load_cache(self, cache_key: str = "default", cache_minutes: int = 15):
        """Load cached data if fresh"""
        if not os.path.exists(self.cache_file):
            return None

        try:
            with open(self.cache_file, 'r') as f:
                cache = json.load(f)

            if cache_key not in cache:
                return None

            entry = cache[cache_key]
            cached_time = datetime.fromisoformat(entry.get('timestamp', '2000-01-01'))

            if datetime.now() - cached_time < timedelta(minutes=cache_minutes):
                return entry.get('data')
            else:
                return None
        except Exception as e:
            return None
        except Exception as e:
            return None

    def _save_cache(self, data, cache_key: str = "default"):
        """Save data to cache file"""
        cache = {}
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
            except:
                cache = {}

        cache[cache_key] = {
            'timestamp': datetime.now().isoformat(),
            'data': data
        }

        with open(self.cache_file, 'w') as f:
            json.dump(cache, f, indent=2)

    def _handle_api_response(self, data: Union[List, Dict]) -> Optional[Union[List, Dict]]:
        """
        Handle API response that could be List or Dict
        - If List: return it directly (it's the data)
        - If Dict with 'message': print error and return None
        - If Dict with data: extract and return
        """
        if isinstance(data, list):
            # API returned list directly - this is the schedule/props
            return data
        
        elif isinstance(data, dict):
            # Check for error message
            if 'message' in data:
                print(f"[API ERROR] {data.get('message')}")
                return None
            
            # Check for common wrapper keys
            if 'data' in data:
                return data['data']
            if 'events' in data:
                return data['events']
            if 'bookmakers' in data:
                # Single event data
                return data
            
            # Return dict as-is if no error
            return data
        
        else:
            print(f"[API ERROR] Unexpected response type: {type(data)}")
            return None

    def get_schedule(self) -> List[Dict]:
        """Fetch NBA schedule from ALL regions"""
        cache_key = "schedule"
        cached = self._load_cache(cache_key, SCHEDULE_CACHE_MINUTES)
        if cached:
            return cached

        # Check for demo/placeholder key
        if not self.api_key or self.api_key == "PLACEHOLDER":
            return self._get_demo_schedule()

        url = f"{self.BASE_URL}/{NBA_SPORT_KEY}/events"
        params = {
            'apiKey': self.api_key,
            'regions': REGIONS,
            'markets': MARKETS,
            'oddsFormat': ODDS_FORMAT
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Handle both List and Dict responses
            handled_data = self._handle_api_response(data)
            
            if handled_data is None:
                return self._get_demo_schedule()
            
            # Ensure we have a list
            if isinstance(handled_data, dict):
                # If single event returned, wrap in list
                handled_data = [handled_data]
            
            self._save_cache(handled_data, cache_key)
            return handled_data
            
        except Exception as e:
            print(f"[API ERROR] {e}")
            return self._get_demo_schedule()

    def get_props_for_game(self, game_id: str) -> List[Dict]:
        """
        Fetch ALL props for a specific game across ALL bookmakers/regions
        Includes book name for every prop
        """
        cache_key = f"props_{game_id}"
        cached = self._load_cache(cache_key, PROPS_CACHE_MINUTES)
        if cached:
            return cached

        # Check for demo/placeholder key or demo game ID
        if not self.api_key or self.api_key == "PLACEHOLDER" or game_id.startswith("demo"):
            return self._get_demo_props(game_id)

        url = f"{self.BASE_URL}/{NBA_SPORT_KEY}/events/{game_id}/odds"
        params = {
            'apiKey': self.api_key,
            'regions': REGIONS,
            'markets': MARKETS,
            'oddsFormat': ODDS_FORMAT
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Handle both List and Dict responses
            handled_data = self._handle_api_response(data)
            
            if handled_data is None:
                return self._get_demo_props(game_id)
            
            # Parse props from the event data
            if isinstance(handled_data, list):
                # If list returned, process first item (shouldn't happen for single event)
                if len(handled_data) > 0:
                    handled_data = handled_data[0]
                else:
                    return self._get_demo_props(game_id)
            
            props = self._parse_props_with_books(handled_data)
            self._save_cache(props, cache_key)
            return props

        except Exception as e:
            print(f"[API ERROR] {e}")
            return self._get_demo_props(game_id)

    def _parse_props_with_books(self, event_data: Dict) -> List[Dict]:
        """Parse event data and extract ALL props from ALL bookmakers"""
        props = []

        event_id = event_data.get('id', 'unknown')
        home_team = event_data.get('home_team', 'TBD')
        away_team = event_data.get('away_team', 'TBD')
        commence_time = event_data.get('commence_time', '')
        matchup = f"{away_team} @ {home_team}"

        bookmakers = event_data.get('bookmakers', [])

        for book in bookmakers:
            book_name = book.get('title', 'Unknown')
            book_key = book.get('key', 'unknown')
            markets = book.get('markets', [])

            for market in markets:
                market_key = market.get('key', '')

                market_display = {
                    'player_points': 'PTS',
                    'player_rebounds': 'REB',
                    'player_assists': 'AST'
                }.get(market_key, market_key.upper())

                for outcome in market.get('outcomes', []):
                    point = outcome.get('point', 0)
                    price = outcome.get('price', 0)
                    name = outcome.get('name', '')
                    description = outcome.get('description', name)

                    # Determine side (Over or Under)
                    side = 'Over' if 'over' in name.lower() else 'Under'

                    props.append({
                        'event_id': event_id,
                        'player': description,
                        'market': market_display,
                        'stat_type': market_key,
                        'side': side,  # Over or Under
                        'line': point,
                        'odds': price,
                        'book': book_name,
                        'book_key': book_key,
                        'matchup': matchup,
                        'commence_time': commence_time
                    })

        return props

    def _get_demo_schedule(self) -> List[Dict]:
        """Return demo schedule when API unavailable"""
        return [
            {
                'id': 'demo1',
                'home_team': 'Boston Celtics',
                'away_team': 'Los Angeles Lakers',
                'commence_time': datetime.now().isoformat()
            },
            {
                'id': 'demo2',
                'home_team': 'Milwaukee Bucks',
                'away_team': 'Phoenix Suns',
                'commence_time': datetime.now().isoformat()
            }
        ]

    def _get_demo_props(self, event_id: str) -> List[Dict]:
        """Return demo props when API unavailable"""
        base_props = [
            {'player': 'LeBron James', 'market': 'PTS', 'stat_type': 'player_points', 'line': 28.5, 'odds': 1.91, 'book': 'DraftKings'},
            {'player': 'LeBron James', 'market': 'PTS', 'stat_type': 'player_points', 'line': 28.5, 'odds': 1.95, 'book': 'Bet365'},
            {'player': 'Jayson Tatum', 'market': 'PTS', 'stat_type': 'player_points', 'line': 26.5, 'odds': 1.91, 'book': 'DraftKings'},
            {'player': 'Jayson Tatum', 'market': 'REB', 'stat_type': 'player_rebounds', 'line': 8.5, 'odds': 1.91, 'book': 'DraftKings'},
        ]

        matchup = "Demo Game"
        for prop in base_props:
            prop['event_id'] = event_id
            prop['matchup'] = matchup
            prop['commence_time'] = datetime.now().isoformat()
            prop['book_key'] = prop['book'].lower().replace(' ', '')

        return base_props
