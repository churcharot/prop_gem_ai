import config
from analyst import PropAnalyst

def run_manual_mode():
    # 1. Wake up the Brain
    print("Initializing Prop Gem AI (DeepSeek R1)...")
    analyst = PropAnalyst()
    
    print("\n--- PROP GEM VALIDATOR ---")
    print("Type 'exit' to quit.\n")

    while True:
        # 2. Ask YOU for the data
        player = input("Enter Player Name (e.g. LeBron James): ")
        if player.lower() == 'exit': break
        
        line = input(f"Enter Line for {player} (e.g. 24.5): ")
        odds = input(f"Enter Odds for {player} (e.g. -110 or 1.91): ")

        print(f"\nAnalyzing {player}...")

        # 3. Send to DeepSeek (The exact same way the main app does)
        result = analyst.analyze_prop(player, line, odds)

        # 4. Show the Verdict
        edge = result.get('edge_percentage', 0)
        rating = result.get('rating', 'Unknown')
        
        print("-" * 30)
        print(f"VERDICT: {rating.upper()}")
        print(f"Edge: {edge * 100:.2f}%")
        print("-" * 30 + "\n")

if __name__ == "__main__":
    run_manual_mode()