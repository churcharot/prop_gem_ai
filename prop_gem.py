"""
Prop Gem AI - Production Dashboard
Trend Hunting + Global Line Shopping
"""

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional

from config import MAX_THREADS, ODDS_API_KEY, OPENROUTER_API_KEY
from fetcher import OddsFetcher
from researcher import get_player_trends
from analyst import get_analysis
from engine import MathEngine


def display_games(games: List[Dict]):
    """Display available games"""
    print("\n" + "="*80)
    print(" AVAILABLE GAMES ".center(80, "="))
    print("="*80)

    for i, game in enumerate(games, 1):
        away = game['away_team']
        home = game['home_team']
        print(f"  [{i}] {away} @ {home}")

    print("="*80)


def get_user_game_selection(games: List[Dict]) -> Optional[Dict]:
    """Get game selection from user"""
    while True:
        try:
            choice = input("\nSelect game number (or 'q' to quit): ").strip()

            if choice.lower() == 'q':
                return None

            idx = int(choice) - 1
            if 0 <= idx < len(games):
                return games[idx]
            else:
                print(f"Invalid selection. Enter 1-{len(games)}")
        except ValueError:
            print("Invalid input. Enter a number or 'q'")


def get_book_filter() -> Optional[str]:
    """Ask user if they want to filter by bookmaker"""
    print("\nFilter by bookmaker?")
    print("  [1] All books (Global line shopping)")
    print("  [2] DraftKings only")
    print("  [3] FanDuel only")
    print("  [4] Bet365 only")

    try:
        choice = input("Select option: ").strip()
    except EOFError:
        print("\n[Auto-selected] All books")
        return None

    filters = {
        '2': 'DraftKings',
        '3': 'FanDuel',
        '4': 'Bet365'
    }

    return filters.get(choice)


def find_better_odds(props: List[Dict], current_prop: Dict) -> Optional[Dict]:
    """Check if another book has better odds for this player/market"""
    player = current_prop['player']
    market = current_prop['market']
    current_odds = current_prop['odds']

    # Map market display to stat_type
    market_to_stat = {'PTS': 'player_points', 'REB': 'player_rebounds', 'AST': 'player_assists'}
    stat_type = market_to_stat.get(market, '')

    better = None
    for p in props:
        if (p['player'] == player and
            p['stat_type'] == stat_type and
            p['odds'] > current_odds and
            abs(p['line'] - current_prop['line']) < 0.5):
            if better is None or p['odds'] > better['odds']:
                better = p

    return better


def process_prop(prop: Dict, engine: MathEngine) -> Optional[Dict]:
    """Process a single prop: Get trends -> Analyze -> Return result"""
    try:
        player = prop['player']
        stat = prop['stat_type'].replace('player_', '')
        line = prop['line']
        odds = prop['odds']
        book = prop['book']

        # Step 1: Get trends (Perplexity Sonar via OpenRouter)
        trends = get_player_trends(player, stat, line)

        # Step 2: Get analysis (DeepSeek R1 via OpenRouter)
        analysis = get_analysis(player, stat, line, odds, trends)

        # Step 3: Calculate Kelly stake
        implied_prob = engine.calculate_implied_probability(odds)
        true_win = engine.calculate_true_win_pct(implied_prob, analysis['edge_percentage'])
        kelly = engine.calculate_kelly_stake(true_win, odds)

        return {
            'player': player,
            'market': prop['market'],
            'line': line,
            'odds': odds,
            'book': book,
            'edge': analysis['edge_percentage'],
            'rating': analysis['rating'],
            'kelly_pct': kelly * 100,
            'last_10': trends.get('last_10_hit_rate', 0),
            'trend_dir': trends.get('trend_direction', '?'),
            'injury': trends.get('has_injury_concern', False),
            'matchup': prop['matchup']
        }

    except Exception as e:
        print(f"[ERROR] Failed to process {prop.get('player', 'unknown')}: {e}")
        return None


def display_results(results: List[Dict], props: List[Dict]):
    """Display the final analysis table"""
    if not results:
        print("\n[WARNING] No results to display")
        return

    # Sort by edge (highest first)
    results.sort(key=lambda x: x['edge'], reverse=True)

    print("\n" + "="*130)
    print(" ANALYSIS RESULTS ".center(130, "="))
    print("="*130)

    # Header
    print(f"\n{'PLAYER':<22} {'MKT':<5} {'LINE':<6} {'EDGE':<8} {'ODDS':<6} "
          f"{'BOOK':<12} {'KELLY':<7} {'TRENDS (L10)':<15} {'ALERT':<20}")
    print("-"*130)

    # Rows
    for r in results:
        if r['rating'] == 'PASS':
            continue

        edge_str = f"{r['edge']:+.1%}"

        trend_str = f"{r['last_10']:.0%} {r['trend_dir'][:3]}"
        if r['injury']:
            trend_str += " [INJ]"

        alert = ""
        better = find_better_odds(props, r)
        if better and better['book'] != r['book']:
            alert = f"Better: {better['book']} {better['odds']}"

        player = r['player'][:21] if len(r['player']) > 22 else r['player']

        print(f"{player:<22} {r['market']:<5} {r['line']:<6.1f} {edge_str:<8} "
              f"{r['odds']:<6.2f} {r['book']:<12} {r['kelly_pct']:<6.1f}% "
              f"{trend_str:<15} {alert:<20}")

    print("-"*130)

    smash_count = sum(1 for r in results if r['rating'] == 'SMASH')
    lean_count = sum(1 for r in results if r['rating'] == 'LEAN')
    total_analyzed = len(results)

    print(f"\nTOTAL: {total_analyzed} props | {smash_count} SMASH | {lean_count} LEAN")

    if results:
        best = results[0]
        if best['rating'] != 'PASS':
            print(f"TOP PLAY: {best['player']} {best['market']} {best['line']} @ {best['odds']} ({best['edge']:+.1%} edge)")

    print("="*130)


def check_api_keys():
    """Check if API keys are configured"""
    issues = []

    if ODDS_API_KEY == "PLACEHOLDER" or not ODDS_API_KEY:
        issues.append("ODDS_API_KEY not set")

    if OPENROUTER_API_KEY == "PLACEHOLDER" or not OPENROUTER_API_KEY:
        issues.append("OPENROUTER_API_KEY not set (simulated mode)")

    if issues:
        print("\n" + "!"*80)
        print(" CONFIGURATION WARNINGS ".center(80, "!"))
        print("!"*80)
        for issue in issues:
            print(f"  [!] {issue}")
        print("!"*80 + "\n")


def main():
    """Main execution flow"""
    print("\n" + "="*80)
    print("          ** PROP GEM AI **")
    print("     Trend Hunting + Global Line Shopping")
    print("="*80)

    check_api_keys()

    fetcher = OddsFetcher()
    engine = MathEngine()

    # Get schedule
    print("\n[1/4] Loading NBA schedule...")
    games = fetcher.get_schedule()

    if not games:
        print("[ERROR] No games found. Check your API key.")
        return

    display_games(games)

    try:
        selected_game = get_user_game_selection(games)
        if not selected_game:
            print("Goodbye!")
            return
    except EOFError:
        selected_game = games[0]
        print(f"\n[AUTO-SELECTED] {selected_game['away_team']} @ {selected_game['home_team']}")

    print(f"\nSelected: {selected_game['away_team']} @ {selected_game['home_team']}")

    # Get props - ONLY pass game_id
    print("\n[2/4] Fetching global odds (all regions)...")
    all_props = fetcher.get_props_for_game(selected_game['id'])

    if not all_props:
        print("[ERROR] No props found for this game.")
        return

    print(f"Found {len(all_props)} props from {len(set(p['book'] for p in all_props))} bookmakers")

    # Book filter
    book_filter = get_book_filter()
    if book_filter:
        props = [p for p in all_props if p['book'] == book_filter]
        print(f"Filtered to {len(props)} props from {book_filter}")
    else:
        props = all_props

    # Deduplicate by player/stat (keep best odds)
    seen = {}
    unique_props = []
    for p in props:
        key = (p['player'], p['stat_type'])
        if key not in seen or p['odds'] > seen[key]['odds']:
            seen[key] = p
    unique_props = list(seen.values())

    print(f"\n[3/4] Analyzing {len(unique_props)} unique props...")
    print(f"      (Using {MAX_THREADS} threads)\n")

    # Process props with threading
    results = []
    completed = 0

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = {
            executor.submit(process_prop, prop, engine): prop
            for prop in unique_props
        }

        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

            completed += 1
            if completed % 5 == 0 or completed == len(unique_props):
                print(f"  Progress: {completed}/{len(unique_props)} complete")

    # Display results
    print("\n[4/4] Analysis complete!")
    display_results(results, all_props)

    try:
        save = input("\nSave results to file? (y/n): ").strip().lower()
        if save == 'y':
            filename = f"props_{selected_game['id'][:8]}.txt"
            with open(filename, 'w') as f:
                f.write("PROP GEM AI - Analysis Results\n")
                f.write(f"Game: {selected_game['away_team']} @ {selected_game['home_team']}\n")
                f.write("="*80 + "\n\n")
                for r in results:
                    if r['rating'] != 'PASS':
                        f.write(f"{r['player']} {r['market']} {r['line']} @ {r['odds']} "
                               f"[{r['book']}] | Edge: {r['edge']:+.1%} | {r['rating']}\n")
            print(f"Results saved to {filename}")
    except EOFError:
        pass

    print("\nGood luck!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Goodbye!")
        sys.exit(0)
