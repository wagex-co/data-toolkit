from .types import MarketTitle

def get_over_under_type(sport: str) -> MarketTitle:
    sport_lower = sport.lower()
    
    if sport_lower in ["football", "basketball", "rugby"]:
        return MarketTitle.TOTAL_POINTS
    elif sport_lower in ["soccer", "hockey"]:
        return MarketTitle.TOTAL_GOALS
    elif sport_lower == "baseball":
        return MarketTitle.TOTAL_RUNS
    elif sport_lower == "tennis":
        return MarketTitle.TOTAL_SETS
    else:
        return MarketTitle.TOTAL_POINTS 

def earnings_calculator(odds: float, amount: float, is_buy: bool, is_win: bool = True) -> float:
    """Calculate earnings based on odds and amount."""
    if not is_win:
        return -amount  # If it's a loss, user loses their stake

    # For wins:
    # Buy: User wins (odds * amount) - amount
    # Sell: User wins amount - (amount / (odds-1))
    if is_buy:
        return (amount * odds) - amount
    else:
        return (amount / (odds-1)) + amount 