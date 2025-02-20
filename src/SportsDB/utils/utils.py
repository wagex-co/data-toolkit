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