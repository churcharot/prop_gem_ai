"""
Prop Gem AI - Utils Module
Odds conversion utilities
"""


class OddsConverter:
    """Convert between different odds formats"""
    
    @staticmethod
    def american_to_decimal(american_odds: int) -> float:
        """Convert American odds to Decimal odds"""
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1
    
    @staticmethod
    def decimal_to_american(decimal_odds: float) -> int:
        """Convert Decimal odds to American odds"""
        if decimal_odds >= 2.0:
            return int((decimal_odds - 1) * 100)
        else:
            return int(-100 / (decimal_odds - 1))
