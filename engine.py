"""
Prop Gem AI - Engine Module
Math logic for Kelly Criterion and probability calculations
"""

from config import RISK_MULTIPLIER


class MathEngine:
    """Calculates betting math: implied probability, true win %, Kelly stake"""

    def __init__(self):
        self.risk_mult = RISK_MULTIPLIER

    def calculate_implied_probability(self, decimal_odds: float) -> float:
        """Step 1: Calculate implied probability from decimal odds"""
        return 1 / decimal_odds

    def calculate_true_win_pct(self, implied_prob: float, edge_pct: float) -> float:
        """Step 2: Calculate true win % = implied probability + edge %"""
        return implied_prob + edge_pct

    def calculate_kelly_stake(self, win_prob: float, decimal_odds: float) -> float:
        """
        Step 3: Calculate Kelly Criterion stake

        Full Kelly: f* = (bp - q) / b
        Where:
        - b = decimal odds - 1
        - p = probability of winning
        - q = probability of losing = 1 - p

        Returns fractional Kelly based on RISK_MULTIPLIER
        """
        b = decimal_odds - 1
        p = win_prob
        q = 1 - p

        if b <= 0:
            return 0

        full_kelly = (b * p - q) / b
        fractional_kelly = full_kelly * self.risk_mult

        return max(0, fractional_kelly)
