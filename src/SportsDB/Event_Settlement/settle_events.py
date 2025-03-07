import aiohttp
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from src.SportsDB.utils.types import (
    MarketUpdate, EventUpdate, EventStatus, MarketStatus, 
    MarketOutcome, EventDictionaryType
)
from src.config.settings import settings
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SportsDBClient:
    """Class responsible for handling communication with the SportsDB API."""
    
    def __init__(self, api_key: str):
        self.base_url = "https://www.thesportsdb.com/api/v1/"
        self.api_key = api_key
        
    async def get_event_details(self, event_id: str) -> Optional[Dict]:
        """Fetch event details from SportsDB API."""
        retries = 0
        max_retries = 5
        retry_wait_time = 60 
        
        while retries <= max_retries:
            try:
                url = f"{self.base_url}json/{self.api_key}/lookupevent.php?id={event_id}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 429:
                            retries += 1
                            if retries <= max_retries:
                                logger.warning(f"Rate limit exceeded. Waiting for {retry_wait_time} seconds before retry {retries}/{max_retries}")
                                await asyncio.sleep(retry_wait_time)
                                continue
                            else:
                                logger.error("Maximum retries reached for rate limit error")
                                return None
                        
                        data = await response.json()
                        return data.get('events', [{}])[0]
            except Exception as e:
                retries += 1
                logger.error(f"Error fetching event details: {e}")
                
                # Wait and retry for any exception as well
                if retries <= max_retries:
                    logger.warning(f"Waiting for {retry_wait_time} seconds before retry {retries}/{max_retries}")
                    await asyncio.sleep(retry_wait_time)
                else:
                    logger.error("Maximum retries reached after encountering errors")
                    return None
        
        return None


class ScoreProcessor:
    """Class responsible for processing and extracting scores from SportsDB data."""
    
    @staticmethod
    def extract_scores(sports_db_event: Dict) -> Optional[Dict[str, int]]:
        """Extract and validate scores from a SportsDB event."""
        if not sports_db_event:
            return None
            
        home_score = sports_db_event.get('intHomeScore', None)
        away_score = sports_db_event.get('intAwayScore', None)
        
        # Check for postponed or cancelled events
        if (("yes" in (sports_db_event.get('strPostponed'), sports_db_event.get('strCancelled')) and 
             (home_score is None or away_score is None)) or 
            sports_db_event.get('strStatus') == "POST"):
            return None
            
        if home_score is None or away_score is None:
            logger.error(f"Missing scores for event {sports_db_event.get('strEvent', 'Unknown')}: home={home_score}, away={away_score}")
            return None
            
        try:
            return {
                'home_score': int(home_score), 
                'away_score': int(away_score)
            }
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid score format: {home_score} - {away_score} for event {sports_db_event.get('strEvent', 'Unknown')}. Error: {e}")
            return None


class MarketSettlementEngine:
    """Class responsible for determining market outcomes based on scores."""
    
    @staticmethod
    def determine_outcome(market: Dict, scores: Dict[str, int]) -> MarketOutcome:
        """Determine the outcome of a market based on scores."""
        if market['type'] == 'moneyline':
            if scores['home_score'] > scores['away_score']:
                return MarketOutcome.HOME
            elif scores['away_score'] > scores['home_score']:
                return MarketOutcome.AWAY
            return MarketOutcome.DRAW
        
        elif market['type'] == 'over_under':
            if not market.get('line'):
                raise ValueError(f"No line provided for over/under market {market['_id']}")
            total_score = scores['home_score'] + scores['away_score']
            line = float(market['line'])
            
            if total_score == line:
                return MarketOutcome.DRAW
            return MarketOutcome.HOME if total_score > line else MarketOutcome.AWAY
        
        raise ValueError(f"Invalid market type: {market['type']}")


class SettleEvents:
    """Main class for settling events and their associated markets."""
    
    def __init__(self):
        self.api_client = SportsDBClient(settings.SPORTSDB_API_KEY)
        self.score_processor = ScoreProcessor()
        self.settlement_engine = MarketSettlementEngine()
        self.failed_events = {}
        self.event_updates = []
        self.event_dictionary = {}
        self.coupled_updates = {}  

    async def gather_scores(self, event_dictionary: EventDictionaryType) -> Tuple[List[str], bool]:
        """Gather scores for events and update the event dictionary."""
        postponed_events = []
        scores_gathered = False

        for event_id, event_info in event_dictionary.items():
            try:
                event_data = event_info.get('eventData', {})
                if not event_data or not event_data.get('sportsdb_id'):
                    self.update_failed_events(event_id, "No sportsdb_id found or no event data")
                    continue  

                sports_db_event = await self.api_client.get_event_details(event_data['sportsdb_id'])
                if not sports_db_event:
                    self.update_failed_events(event_id, "No sportsdb event found")
                    continue  
                
                if sports_db_event.get('strPostponed') == "yes":
                    logger.info(f"Event {event_id} is postponed/cancelled")
                    postponed_events.append(event_id)
                    continue  
                
                # Process scores
                scores = self.score_processor.extract_scores(sports_db_event)
                if scores is None:
                    if sports_db_event.get('strStatus') == "POST":
                        logger.info(f"Event {event_id} is postponed/cancelled")
                        postponed_events.append(event_id)
                        continue  
                    self.update_failed_events(event_id, "No scores found or error extracting scores")
                    continue 

                if 'eventData' in event_dictionary[event_id]:
                    event_dictionary[event_id]['eventData']['scores'] = scores
                    scores_gathered = True
                    
            except Exception as e:
                logger.error(f"Error processing event {event_id}: {e}")
                self.update_failed_events(event_id, f"Error processing event {event_id}: {e}")
                
        return postponed_events, scores_gathered
    
    def create_settlement_updates(self) -> None:
        """Create market and event updates based on the scores in the event dictionary."""
        for event_id, event_info in self.event_dictionary.items():
            if event_id in self.failed_events:
                continue

            event_data = event_info.get('eventData', {})
            scores = event_data.get('scores')
            if not scores:
                self.update_failed_events(event_id, "No scores found")
                continue
            
            self.coupled_updates[event_id] = {
                "event_update": None,
                "market_updates": []
            }
            
            if not self._process_markets(event_id, event_info, scores):
                self.update_failed_events(event_id, "No markets found")
                continue

            event_update = EventUpdate(
                event_id=event_id,
                result=f"{scores['home_score']}-{scores['away_score']}",
                status=EventStatus.COMPLETED
            )
            self.event_updates.append(event_update)
            self.coupled_updates[event_id]["event_update"] = event_update.model_dump()
    
    def _process_markets(self, event_id: str, event_info: Dict, scores: Dict[str, int]) -> bool:
        """Process all markets for an event and create market updates."""
        for key, market in event_info.items():
            if key == 'eventData':
                continue
                
            if isinstance(market, dict) and market.get('type'):
                market_id = market.get('_id')
                
                if not market_id:
                    return False
                
                try:
                    outcome = self.settlement_engine.determine_outcome(market, scores)
                    
                    market_update = MarketUpdate(
                        market_id=market_id,
                        outcome=outcome,
                        status=MarketStatus.CLOSED
                    )
                    self.coupled_updates[event_id]["market_updates"].append(market_update.model_dump())
                    
                except ValueError as e:
                    logger.error(f"Error determining outcome for market {market_id}: {e}")
                    return False
            else:
                return False
        return True

    def update_failed_events(self, event_id: str, error_message: str) -> None:
        if event_id not in self.failed_events:
            self.failed_events[event_id] = error_message
        else:
            self.failed_events[event_id] += f"\n{error_message}"
    
    async def settle_events(self, event_dictionary: EventDictionaryType) -> Dict[str, Any]:
        """Main method to settle events."""
        logger.info(f"Settingtle events for {len(event_dictionary)} events")
        self.event_dictionary = event_dictionary
        self.coupled_updates = {} 
        self.failed_events = {}    
        
        try:
            postponed_events, scores_gathered = await self.gather_scores(self.event_dictionary)
            
            if not postponed_events and not scores_gathered and not self.failed_events:
                logger.info("No events to settle - no scores gathered and no postponed events")
                return {
                    "message": "No events to settle",
                    "events": {}  
                }
                
            self.create_settlement_updates()
            
            for event_id in postponed_events:
                event_update = {
                    "event_id": event_id,
                    "status": EventStatus.CANCELLED,
                    "result": None,
                    "is_settled": True
                }
                
                market_updates = []
                event_info = self.event_dictionary.get(event_id, {})
                for key, market in event_info.items():
                    if key == 'eventData':
                        continue
                        
                    if isinstance(market, dict) and market.get('type'):
                        market_id = market.get('_id')
                        if market_id:
                            market_updates.append({
                                "market_id": market_id,
                                "status": MarketStatus.CLOSED,
                                "outcome": None  
                            })
                
                self.coupled_updates[event_id] = {
                    "event_update": event_update,
                    "market_updates": market_updates
                }
            
            for event_id, error in self.failed_events.items():
                    self.coupled_updates[event_id] = f"FATAL ERROR: {error}"
            
            for event_id in event_dictionary:
                if event_id not in self.coupled_updates:
                    logger.warning(f"Event {event_id} was not processed during settlement")
                    self.coupled_updates[event_id] = "FATAL ERROR: Event was not processed during settlement"

            logger.info(f"Processing complete. Events: {len(event_dictionary)}, "
                       f"Successful: {len([k for k, v in self.coupled_updates.items() if isinstance(v, dict)])}, "
                       f"Failed: {len([k for k, v in self.coupled_updates.items() if isinstance(v, str)])}")
       
            return {
                "message": "Settlement completed successfully",
                "events": self.coupled_updates,  
                "updated_dictionary": self.event_dictionary
            }
            
        except Exception as e:
            logger.error(f"Error in settlement process: {e}")
            # In case of a critical error, create FATAL ERROR messages for all events
            for event_id in event_dictionary:
                if event_id not in self.coupled_updates:
                    self.coupled_updates[event_id] = f"FATAL ERROR: Global settlement error: {e}"
            
            # Return what we have so far
            return {
                "message": f"Settlement process error: {e}",
                "events": self.coupled_updates,
                "updated_dictionary": self.event_dictionary
            }

# Create a singleton instance
settle_events = SettleEvents() 