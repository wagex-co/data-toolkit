import aiohttp
import logging
from typing import List, Dict, Tuple, Optional
from ...utils.types import (
    EventSettlementData, MarketUpdate, EventUpdate, PayoutData,
    UserPayout, PayoutOrder, EventStatus, MarketStatus, MarketOutcome,
    OrderStatus, OrderSide
)
from ...config.settings import settings
from ...utils.utils import earnings_calculator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SettleEvents:
    def __init__(self):
        self.base_url = "https://www.thesportsdb.com/api/v1/"
        self.api_key = settings.SPORTSDB_API_KEY

    async def get_event_scores(self, event_id: str) -> Optional[Dict]:
        """Fetch event scores from SportsDB API."""
        try:
            url = f"{self.base_url}json/{self.api_key}/lookupevent.php?id={event_id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    data = await response.json()
                    return data.get('events', [{}])[0]
        except Exception as e:
            logger.error(f"Error fetching event scores: {e}")
            return None

    async def gather_event_scores(
        self, 
        unsettled_events: List[Dict]
    ) -> Tuple[List[EventSettlementData], List[str]]:
        """Gather scores for unsettled events."""
        event_data: List[EventSettlementData] = []
        postponed_events: List[str] = []

        for event in unsettled_events:
            try:
                sports_db_event = await self.get_event_scores(event['sportsdb_id'])
                
                if not sports_db_event:
                    continue

                if sports_db_event.get('strPostponed') == "yes":
                    logger.info(f"Event {event['_id']} is postponed/cancelled")
                    postponed_events.append(event['_id'])
                    continue

                home_score = int(sports_db_event.get('intHomeScore', 0) or 0)
                away_score = int(sports_db_event.get('intAwayScore', 0) or 0)

                if home_score == 0 and away_score == 0:
                    logger.info(f"Skipping event {event['_id']} - scores not available")
                    continue

                event_data.append(EventSettlementData(
                    event_id=event['_id'],
                    sportsdb_id=event['sportsdb_id'],
                    scores={'home_score': home_score, 'away_score': away_score}
                ))

            except Exception as e:
                logger.error(f"Error processing event {event['_id']}: {e}")

        return event_data, postponed_events

    def process_settlements(
        self,
        event_data: List[EventSettlementData],
        markets: List[Dict],
        orders: List[Dict]
    ) -> Tuple[List[MarketUpdate], List[EventUpdate], List[PayoutData]]:
        """Process settlements for events, markets, and orders."""
        market_updates: List[MarketUpdate] = []
        event_updates: List[EventUpdate] = []
        payout_data: List[PayoutData] = []

        for data in event_data:
            if not data.scores:
                continue

            event_markets = [m for m in markets if m['event_id'] == data.event_id]
            
            for market in event_markets:
                outcome = self._determine_market_outcome(market, data.scores)
                
                market_updates.append(MarketUpdate(
                    market_id=market['_id'],
                    outcome=outcome,
                    status=MarketStatus.CLOSED
                ))

                market_orders = [o for o in orders if o['market_id'] == market['_id']]
                payout_data.extend(self._process_orders(market_orders, outcome))

            event_updates.append(EventUpdate(
                event_id=data.event_id,
                result=f"{data.scores['home_score']}-{data.scores['away_score']}",
                status=EventStatus.COMPLETED
            ))

        return market_updates, event_updates, payout_data

    def _determine_market_outcome(
        self, 
        market: Dict, 
        scores: Dict[str, int]
    ) -> MarketOutcome:
        """Determine the outcome of a market based on scores."""
        if market['type'] == 'moneyline':
            if scores['home_score'] > scores['away_score']:
                return MarketOutcome.HOME
            elif scores['away_score'] > scores['home_score']:
                return MarketOutcome.AWAY
            return MarketOutcome.DRAW
        
        elif market['type'] == 'over_under' and market.get('line'):
            total_score = scores['home_score'] + scores['away_score']
            line = float(market['line'])
            
            if total_score == line:
                return MarketOutcome.DRAW
            return MarketOutcome.HOME if total_score > line else MarketOutcome.AWAY

        return MarketOutcome.DRAW

    def _process_orders(
        self, 
        orders: List[Dict], 
        outcome: MarketOutcome
    ) -> List[PayoutData]:
        """Process orders and calculate payouts."""
        payout_data = []

        for order in orders:
            if order['status'] == OrderStatus.OPEN:
                payout_data.append(PayoutData(
                    order_id=order['_id'],
                    user_id=order['user_id'],
                    reward_amount=order['amount'],
                    withheld_amount=order['amount'],
                    market_id=order['market_id'],
                    status=OrderStatus.EXPIRED
                ))
                continue

            new_status, payout_amount = self._calculate_order_result(order, outcome)
            
            payout_data.append(PayoutData(
                order_id=order['_id'],
                user_id=order['user_id'],
                reward_amount=payout_amount,
                withheld_amount=order['amount'],
                market_id=order['market_id'],
                status=new_status
            ))

        return payout_data

    def _calculate_order_result(
        self, 
        order: Dict, 
        outcome: MarketOutcome
    ) -> Tuple[OrderStatus, float]:
        """Calculate the result and payout amount for an order."""
        if outcome == MarketOutcome.DRAW:
            return OrderStatus.PUSH, order['filled_amount']

        is_buy = order['side'] == OrderSide.BUY
        is_win = (outcome == MarketOutcome.HOME and is_buy) or \
                (outcome == MarketOutcome.AWAY and not is_buy)

        odds = order.get('fulfilled_odds', order['odds'])
        payout = earnings_calculator(
            odds=odds,
            amount=order['filled_amount'],
            is_buy=is_buy,
            is_win=is_win
        )

        return OrderStatus.WON if is_win else OrderStatus.LOST, payout

    def process_batch_payouts(self, payout_data: List[PayoutData]) -> List[UserPayout]:
        """Process batch payouts for users."""
        user_payouts: Dict[str, UserPayout] = {}

        for payout in payout_data:
            if payout.user_id not in user_payouts:
                user_payouts[payout.user_id] = UserPayout(
                    user_id=payout.user_id,
                    total_reward_amount=0,
                    total_withheld_amount=0,
                    orders=[]
                )

            user_payout = user_payouts[payout.user_id]
            user_payout.total_reward_amount += payout.reward_amount
            user_payout.total_withheld_amount += payout.withheld_amount
            user_payout.orders.append(PayoutOrder(
                order_id=payout.order_id,
                reward_amount=payout.reward_amount,
                withheld_amount=payout.withheld_amount,
                market_id=payout.market_id,
                status=payout.status
            ))

        return list(user_payouts.values())

    async def settle_markets(
        self,
        unsettled_events: List[Dict],
        markets: List[Dict],
        orders: List[Dict]
    ) -> Dict:
        """Main method to settle markets."""
        try:
            event_data, postponed_events = await self.gather_event_scores(unsettled_events)
            
            if not event_data and not postponed_events:
                return {
                    "message": "No events to settle",
                    "settled_events": [],
                    "postponed_events": [],
                    "market_updates": [],
                    "payout_data": [],
                    "batch_payouts": []
                }

            market_updates, event_updates, payout_data = self.process_settlements(
                event_data, markets, orders
            )
            
            batch_payouts = self.process_batch_payouts(payout_data)

            return {
                "message": "Settlement completed successfully",
                "settled_events": [e.model_dump() for e in event_updates],
                "postponed_events": postponed_events,
                "market_updates": [m.model_dump() for m in market_updates],
                "payout_data": [p.model_dump() for p in payout_data],
                "batch_payouts": [p.model_dump() for p in batch_payouts]
            }

        except Exception as e:
            logger.error(f"Error in settlement process: {e}")
            raise

settle_events = SettleEvents() 