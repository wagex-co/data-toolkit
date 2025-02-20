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