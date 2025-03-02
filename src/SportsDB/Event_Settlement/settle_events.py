import aiohttp
import logging
from typing import List, Dict, Tuple, Optional
from src.SportsDB.utils.types import (
    EventSettlementData, MarketUpdate, EventUpdate,
    EventStatus, MarketStatus, MarketOutcome
)
from src.config.settings import settings

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
        markets: List[Dict]
    ) -> Tuple[List[MarketUpdate], List[EventUpdate]]:
        """Process settlements for events and markets."""
        market_updates: List[MarketUpdate] = []
        event_updates: List[EventUpdate] = []

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

            event_updates.append(EventUpdate(
                event_id=data.event_id,
                result=f"{data.scores['home_score']}-{data.scores['away_score']}",
                status=EventStatus.COMPLETED
            ))

        return market_updates, event_updates

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

    async def settle_markets(
        self,
        unsettled_events: List[Dict],
        markets: List[Dict]
    ) -> Dict:
        """Main method to settle markets."""
        try:
            event_data, postponed_events = await self.gather_event_scores(unsettled_events)
            
            if not event_data and not postponed_events:
                return {
                    "message": "No events to settle",
                    "settled_events": [],
                    "postponed_events": [],
                    "market_updates": []
                }

            market_updates, event_updates = self.process_settlements(
                event_data, markets
            )

            return {
                "message": "Settlement completed successfully",
                "settled_events": [e.model_dump() for e in event_updates],
                "postponed_events": postponed_events,
                "market_updates": [m.model_dump() for m in market_updates]
            }

        except Exception as e:
            logger.error(f"Error in settlement process: {e}")
            raise

settle_events = SettleEvents() 