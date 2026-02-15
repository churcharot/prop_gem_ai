"""
Prop Gem AI - Streamlit Web Application
Interactive player prop analysis with AI-powered edge detection
"""

import streamlit as st
import pandas as pd
from typing import Dict
from fetcher import OddsFetcher
from researcher import TrendResearcher
from analyst import PropAnalyst

# Page configuration
st.set_page_config(
    page_title="Prop Gem AI",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        color: #ffd700;
    }
    .main-header {
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        color: white;
        margin: 0;
    }
    .smash-row {
        background-color: rgba(34, 197, 94, 0.3) !important;
        font-weight: bold;
    }
    .lean-row {
        background-color: rgba(234, 179, 8, 0.2) !important;
    }
    .stDataFrame {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
    }
    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e3a5f 0%, #0d1b2a 100%);
    }
    .success-box {
        background: linear-gradient(90deg, #22c55e 0%, #16a34a 100%);
        padding: 1rem;
        border-radius: 8px;
        color: white;
        text-align: center;
        margin: 1rem 0;
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.1);
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)


def check_password():
    """Password lock at the start of the app"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.markdown("""
        <div style="text-align: center; padding: 3rem;">
            <h1 style="color: #667eea;">💎 Prop Gem AI</h1>
            <p style="color: #94a3b8;">AI-Powered Player Prop Analysis</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            password = st.text_input("Enter Password", type="password", key="password_input")
            if st.button("🔓 Unlock", use_container_width=True):
                if password == "gem2026":
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("❌ Incorrect password. Try again.")
        return False
    return True


def get_books_from_props(props):
    """Extract unique book names from props list"""
    books = set()
    for prop in props:
        if 'book' in prop:
            books.add(prop['book'])
    return sorted(list(books))


def format_results_dataframe(results):
    """Format analysis results into a styled DataFrame"""
    if not results:
        return None
    
    df = pd.DataFrame(results)
    
    # Reorder columns for display
    display_cols = ['player', 'market', 'side', 'line', 'odds', 'book', 'better_lines', 'edge_pct', 'rating', 'confidence', 'reasoning']
    available_cols = [col for col in display_cols if col in df.columns]
    df = df[available_cols]
    
    return df


def style_dataframe(df):
    """Apply styling to the results dataframe"""
    def highlight_rating(row):
        try:
            rating = row['rating']
            if rating == 'SMASH':
                return ['background-color: rgba(34, 197, 94, 0.4)'] * len(row)
            elif rating == 'LEAN':
                return ['background-color: rgba(234, 179, 8, 0.3)'] * len(row)
        except (KeyError, TypeError):
            pass
        return [''] * len(row)
    
    return df.style.apply(highlight_rating, axis=1)


def run_analysis(game_id, selected_book, progress_placeholder, all_game_props):
    """Run the Fetcher -> Researcher -> Analyst workflow with line shopping"""
    results = []
    
    # Initialize modules with secrets
    import config
    config.ODDS_API_KEY = st.secrets.get("ODDS_API_KEY", config.ODDS_API_KEY)
    config.OPENROUTER_API_KEY = st.secrets.get("OPENROUTER_API_KEY", config.OPENROUTER_API_KEY)
    
    fetcher = OddsFetcher()
    researcher = TrendResearcher()
    analyst = PropAnalyst()
    
    # Use provided props
    props = all_game_props
    
    if not props:
        progress_placeholder.error("No props found for this game.")
        return []
    
    # Build a lookup of ALL odds across ALL books for line shopping
    # Key: player_market_side_line -> List of {book, odds}
    all_odds_lookup: Dict[str, list] = {}
    for prop in props:
        side = prop.get('side', 'Over')
        key = f"{prop['player']}_{prop['market']}_{side}_{prop['line']}"
        if key not in all_odds_lookup:
            all_odds_lookup[key] = []
        all_odds_lookup[key].append({
            'book': prop['book'],
            'odds': prop['odds']
        })
    
    # Sort each prop's books by odds (best first)
    for key in all_odds_lookup:
        all_odds_lookup[key].sort(key=lambda x: x['odds'], reverse=True)
    
    # Filter props by selected book for analysis (but we'll still show best odds)
    if selected_book and selected_book != "All Books":
        props_to_use = [p for p in props if p.get('book') == selected_book]
    else:
        # When "All Books" selected, deduplicate to get unique player/stat/side/line combos
        seen = set()
        props_to_use = []
        for p in props:
            side = p.get('side', 'Over')
            key = f"{p['player']}_{p['market']}_{side}_{p['line']}"
            if key not in seen:
                seen.add(key)
                props_to_use.append(p)
    
    if not props_to_use:
        progress_placeholder.error(f"No props found for {selected_book}.")
        return []
    
    # Sort by odds (best value props first) and take top 30
    props_to_use.sort(key=lambda x: x.get('odds', 0), reverse=True)
    props_to_analyze = props_to_use[:30]
    
    total = len(props_to_analyze)
    progress_placeholder.info(f"🔍 Analyzing {total} props with line shopping...")
    
    progress_bar = st.progress(0)
    
    for i, prop in enumerate(props_to_analyze):
        # Step 2: Research trends
        side = prop.get('side', 'Over')
        trends = researcher.get_player_trends(
            player=prop['player'],
            stat=prop['market'],
            line=prop['line'],
            side=side
        )
        
        # Get best odds from line shopping
        # Key includes side now
        key = f"{prop['player']}_{prop['market']}_{side}_{prop['line']}"
        book_odds_list = all_odds_lookup.get(key, [])
        
        # The prop's odds are from the selected book
        selected_book_odds = prop['odds']
        selected_book_name = prop['book']
        
        # Find better alternatives (odds higher than selected book)
        better_lines = []
        for item in book_odds_list:
            if item['odds'] > selected_book_odds and item['book'] != selected_book_name:
                better_lines.append(f"{item['book']}: {item['odds']:.2f}")
        better_lines_str = " | ".join(better_lines[:3]) if better_lines else "-"
        
        # For AI analysis, use the BEST available odds (for accurate edge calculation)
        best_odds = book_odds_list[0]['odds'] if book_odds_list else selected_book_odds
        
        # Step 3: Analyze with AI (use BEST odds for analysis)
        analysis = analyst.analyze_prop(
            player=prop['player'],
            stat=prop['market'],
            line=prop['line'],
            odds=best_odds,  # Use best odds for edge calculation
            trends=trends,
            side=side
        )
        
        # Combine results - show SELECTED BOOK odds, with better alternatives
        result = {
            'player': prop['player'],
            'market': prop['market'],
            'side': side,
            'line': prop['line'],
            'odds': selected_book_odds,  # Show selected book's odds
            'book': selected_book_name,   # Show selected book
            'better_lines': better_lines_str,  # Show better alternatives
            'edge_pct': f"{analysis['edge_percentage']:.1%}",
            'rating': analysis['rating'],
            'confidence': analysis['confidence'],
            'reasoning': analysis['reasoning'][:150] + "..." if len(analysis['reasoning']) > 150 else analysis['reasoning']
        }
        results.append(result)
        
        # Update progress
        progress_bar.progress((i + 1) / total)
    
    progress_bar.empty()
    progress_placeholder.success(f"✅ Analysis complete! Found {len(results)} props.")
    
    return results



def main():
    """Main application logic"""
    
    # Password check
    if not check_password():
        return
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>💎 Prop Gem AI</h1>
        <p style="color: rgba(255,255,255,0.8); margin: 0;">AI-Powered Player Prop Edge Detection</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize fetcher with secrets
    import config
    config.ODDS_API_KEY = st.secrets.get("ODDS_API_KEY", config.ODDS_API_KEY)
    config.OPENROUTER_API_KEY = st.secrets.get("OPENROUTER_API_KEY", config.OPENROUTER_API_KEY)
    
    fetcher = OddsFetcher()
    
    # Sidebar
    st.sidebar.markdown("## 🎮 Game Selection")
    
    # Fetch schedule
    with st.spinner("Loading games..."):
        schedule = fetcher.get_schedule()
    
    if not schedule:
        st.sidebar.error("No games available.")
        return
    
    # Create game options
    game_options = {}
    for game in schedule:
        game_id = game.get('id', 'unknown')
        home = game.get('home_team', 'TBD')
        away = game.get('away_team', 'TBD')
        matchup = f"{away} @ {home}"
        game_options[matchup] = game_id
    
    selected_game = st.sidebar.selectbox(
        "Select Game",
        options=list(game_options.keys()),
        index=0
    )
    
    game_id = game_options[selected_game]
    
    # Fetch props to get book list
    with st.spinner("Loading books..."):
        props = fetcher.get_props_for_game(game_id)
    
    books = ["All Books"] + get_books_from_props(props)
    
    st.sidebar.markdown("## 📚 Sportsbook Selection")
    selected_book = st.sidebar.selectbox(
        "Select Book",
        options=books,
        index=0
    )
    
    st.sidebar.markdown("---")
    
    # Analyze button
    analyze_clicked = st.sidebar.button(
        "🔍 Analyze Props",
        use_container_width=True,
        type="primary"
    )
    
    # About section
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    ### 📊 Rating Legend
    - 🟢 **SMASH**: Edge ≥ 10%
    - 🟡 **LEAN**: Edge 3-9%
    - ⚪ **PASS**: Edge 0-2%
    - 🔴 **FADE**: Edge < 0%
    """)
    
    # Create tabs for different modes
    tab1, tab2 = st.tabs(["🎮 Game Scanner", "✏️ Manual Analyzer"])
    
    # ============ TAB 1: GAME SCANNER ============
    with tab1:
        if analyze_clicked:
            progress_placeholder = st.empty()
            
            results = run_analysis(game_id, selected_book, progress_placeholder, props)
            
            if results:
                # Sort by rating priority (SMASH first)
                rating_order = {'SMASH': 0, 'LEAN': 1, 'PASS': 2, 'FADE': 3}
                results.sort(key=lambda x: rating_order.get(x['rating'], 3))
                
                # Count smash plays
                smash_count = sum(1 for r in results if r['rating'] == 'SMASH')
                lean_count = sum(1 for r in results if r['rating'] == 'LEAN')
                
                # Metrics row
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📊 Props Analyzed", len(results))
                with col2:
                    st.metric("🟢 SMASH Plays", smash_count)
                with col3:
                    st.metric("🟡 LEAN Plays", lean_count)
                with col4:
                    st.metric("📚 Book", selected_book if selected_book != "All Books" else "All")
                
                st.markdown("---")
                
                # Results table
                st.markdown("### 📋 Analysis Results")
                
                df = format_results_dataframe(results)
                if df is not None:
                    styled_df = style_dataframe(df)
                    st.dataframe(
                        styled_df,
                        use_container_width=True,
                        hide_index=True,
                        height=500
                    )
                
                # SMASH plays highlight
                smash_plays = [r for r in results if r['rating'] == 'SMASH']
                if smash_plays:
                    st.markdown("### 💎 SMASH Plays")
                    for play in smash_plays:
                        better = f" | Better: {play['better_lines']}" if play['better_lines'] != "-" else ""
                        prefix = "O" if play['side'] == "Over" else "U"
                        st.markdown(f"""
                        <div class="success-box">
                            <strong>{play['player']}</strong> - {prefix}{play['line']} {play['market']} @ {play['odds']:.2f}<br>
                            <small>Edge: {play['edge_pct']} | {play['confidence']} Confidence | {play['book']}{better}</small>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            # Welcome screen
            st.markdown("""
            <div style="text-align: center; padding: 3rem; color: #94a3b8;">
                <h2>👈 Select a game and click "Analyze Props"</h2>
                <p>The AI will analyze player props and identify edge opportunities.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Show available games preview
            st.markdown("### 🏀 Today's Games")
            for game in schedule:
                home = game.get('home_team', 'TBD')
                away = game.get('away_team', 'TBD')
                st.markdown(f"- **{away}** @ **{home}**")
    
    # ============ TAB 2: MANUAL ANALYZER ============
    with tab2:
        st.markdown("### ✏️ Analyze a Single Prop")
        st.markdown("Enter prop details below to get an instant AI analysis.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            manual_player = st.text_input("Player Name", placeholder="e.g. LeBron James")
            manual_stat = st.selectbox(
                "Stat Type",
                options=["Points", "Rebounds", "Assists"],
                index=0
            )
        
        with col2:
            manual_line = st.number_input("Line", min_value=0.5, max_value=100.0, value=25.5, step=0.5)
            manual_odds = st.number_input("Odds (Decimal)", min_value=1.01, max_value=10.0, value=1.91, step=0.01)
        
        # Map stat type to API format
        stat_map = {"Points": "PTS", "Rebounds": "REB", "Assists": "AST"}
        stat_type_api = stat_map.get(manual_stat, "PTS")
        
        analyze_manual = st.button("🔍 Analyze This Prop", use_container_width=True, type="primary")
        
        if analyze_manual:
            if not manual_player.strip():
                st.error("Please enter a player name.")
            else:
                with st.spinner("🔍 Researching trends and analyzing..."):
                    # Initialize researcher and analyst
                    researcher = TrendResearcher()
                    analyst = PropAnalyst()
                    
                    # Step 1: Research trends
                    trends = researcher.get_player_trends(
                        player=manual_player,
                        stat=stat_type_api,
                        line=manual_line
                    )
                    
                    # Step 2: Analyze with AI
                    analysis = analyst.analyze_prop(
                        player=manual_player,
                        stat=stat_type_api,
                        line=manual_line,
                        odds=manual_odds,
                        trends=trends
                    )
                
                # Display result
                edge = analysis['edge_percentage']
                rating = analysis['rating']
                confidence = analysis['confidence']
                reasoning = analysis['reasoning']
                
                # Color based on rating
                if rating == 'SMASH':
                    color = "#22c55e"
                    emoji = "🟢"
                elif rating == 'LEAN':
                    color = "#eab308"
                    emoji = "🟡"
                elif rating == 'FADE':
                    color = "#ef4444"
                    emoji = "🔴"
                else:
                    color = "#94a3b8"
                    emoji = "⚪"
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, {color}33 0%, {color}11 100%); 
                            border-left: 4px solid {color}; padding: 1.5rem; border-radius: 8px; margin: 1rem 0;">
                    <h3 style="margin: 0; color: {color};">{emoji} {rating}</h3>
                    <p style="margin: 0.5rem 0; font-size: 1.2rem;">
                        <strong>{manual_player}</strong> O{manual_line} {manual_stat} @ {manual_odds}
                    </p>
                    <p style="margin: 0.5rem 0;">
                        <strong>Edge:</strong> {edge:.1%} | <strong>Confidence:</strong> {confidence}
                    </p>
                    <p style="margin: 0.5rem 0; color: #94a3b8;">
                        <strong>Analysis:</strong> {reasoning}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                # Show trend data
                with st.expander("📈 Trend Research Data"):
                    st.write(f"**Last 10 Hit Rate:** {trends.get('last_10_hit_rate', 0):.0%}")
                    st.write(f"**Trend Direction:** {trends.get('trend_direction', 'Unknown')}")
                    st.write(f"**Injury Concern:** {'Yes' if trends.get('has_injury_concern') else 'No'}")
                    if trends.get('raw_notes'):
                        st.write(f"**Notes:** {trends.get('raw_notes', '')[:200]}...")


if __name__ == "__main__":
    main()
