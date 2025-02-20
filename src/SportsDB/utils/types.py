from pydantic import BaseModel
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime

class EventStatus(str, Enum):
    FUTURE = "future"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class MarketType(str, Enum):
    MONEYLINE = "moneyline"
    SPREAD = "spread"
    OVER_UNDER = "over_under"
    PLAYER_PROP = "player_prop"

class MarketStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"

class MarketTitle(str, Enum):
    MONEYLINE = "Moneyline"
    TOTAL_POINTS = "Total Points"
    TOTAL_GOALS = "Total Goals"
    TOTAL_SETS = "Total Sets"
    TOTAL_RUNS = "Total Runs"

class MarketOutcome(str, Enum):
    HOME = "home"
    AWAY = "away"
    DRAW = "draw"

class SportsDBEvent(BaseModel):
    idEvent: str
    strSport: str
    strLeague: str
    strHomeTeam: str
    strAwayTeam: str
    strEvent: str
    strTimestamp: str
    strVenue: str
    strStatus: str
    intHomeScore: Optional[str]
    intAwayScore: Optional[str]

class MappedEvent(BaseModel):
    sport: str
    league: str
    participants: List[str]
    title: str
    start: str
    status: EventStatus
    location: Optional[str]
    is_settled: bool = False
    sportsdb_id: str

class ApiResponse(BaseModel):
    events: Optional[List[SportsDBEvent]]

class OrderStatus(str, Enum):
    WON = "won"
    LOST = "lost"
    PUSH = "push"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class PayoutOrder(BaseModel):
    order_id: str
    reward_amount: float
    withheld_amount: float
    market_id: str
    status: OrderStatus

class UserPayout(BaseModel):
    user_id: str
    total_reward_amount: float
    total_withheld_amount: float
    orders: List[PayoutOrder]

class EventSettlementData(BaseModel):
    event_id: str
    sportsdb_id: str
    scores: Optional[Dict[str, int]]

class MarketUpdate(BaseModel):
    market_id: str
    outcome: MarketOutcome
    status: MarketStatus

class EventUpdate(BaseModel):
    event_id: str
    is_settled: bool = True
    result: str
    status: EventStatus

class PayoutData(BaseModel):
    order_id: str
    user_id: str
    reward_amount: float
    withheld_amount: float
    market_id: str
    status: OrderStatus 