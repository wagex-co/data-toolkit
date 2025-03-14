import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from dateutil.parser import parse
from src.SportsDB.utils.types import SportsDBEvent, MappedEvent, ApiResponse, EventStatus, MarketType 
from src.config.settings import settings
from src.SportsDB.utils.utils import get_over_under_type

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CreateEvents:
    def __init__(self):
        self.base_url = "https://www.thesportsdb.com/api/v1/"
        self.api_key = settings.SPORTSDB_API_KEY
        self.request_count = 0

    async def get_league_events(
        self, 
        league_id: str, 
        league_name: str,
        date: str, 
        retry_count: int = 0
    ) -> Optional[ApiResponse]:
        self.request_count += 1

        if self.request_count >= 100:
            logger.info('Rate limit approaching - pausing for 60 seconds...')
            await asyncio.sleep(60)
            self.request_count = 0

        try:
            url = f"{self.base_url}json/{self.api_key}/eventsday.php?d={date}&l={league_id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 429 and retry_count < 3:
                        logger.info(f"Rate limit hit, attempt {retry_count + 1}/3 - waiting 60 seconds...")
                        await asyncio.sleep(60)
                        self.request_count = 0
                        return await self.get_league_events(league_id, league_name, date, retry_count + 1)
                    
                    data = await response.json()
                    return ApiResponse(**data)
        except Exception as e:
            logger.error(f"Error fetching league events: {e}")
            return None

    def status_mapper(self, status: str) -> EventStatus:
        if status in ["NS", "Not Started"]:
            return EventStatus.FUTURE
        if status in ["1H", "2H"]:
            return EventStatus.ONGOING
        return EventStatus.COMPLETED

    def map_to_events(self, data: List[SportsDBEvent], league_name: str) -> List[MappedEvent]:
        mapped_events = []
        for item in data:
            sport = "Football" if item.strSport == "American Football" else item.strSport
            timestamp = item.strTimestamp + 'Z' if not item.strTimestamp.endswith('Z') else item.strTimestamp
            
            mapped_event = MappedEvent(
                sport=sport,
                league=league_name,
                participants=[item.strHomeTeam, item.strAwayTeam],
                title=item.strEvent,
                start=timestamp,
                status=self.status_mapper(item.strStatus),
                location=item.strVenue,
                sportsdb_id=item.idEvent
            )
            mapped_events.append(mapped_event)
        return mapped_events

    async def create_events(
        self,
        leagues: Dict[str, str],
        days_to_fetch: int = 7,
        start_date: Optional[str] = None,
    ) -> Tuple[List[Dict], List[Dict]]:
        logger.info(f"Creating events for {len(leagues)} leagues, {days_to_fetch} days, starting from {start_date}")
        start = parse(start_date) if start_date else datetime.now()
        dates = [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days_to_fetch)]
        
        all_events = []
        for league_name, league_id in leagues.items():
            logger.info(f"Getting events for {league_name}")
            for date in dates:
                logger.info(f"Getting events for {date}")
                response = await self.get_league_events(league_id, league_name, date)
                if response and response.events:
                    all_events.extend(self.map_to_events(response.events, league_name))

        logger.info(f"Created {len(all_events)} events")

        events_data = []
        markets_data = []

        # Create events and markets data
        for event in all_events:
            event_dict = event.model_dump()
            events_data.append(event_dict)
            
            # Create markets data
            markets_data.extend([
                {
                    "event_id": event.sportsdb_id,
                    "type": MarketType.MONEYLINE.value,
                    "title": f"{event.participants[0]} Moneyline",
                },
                {
                    "event_id": event.sportsdb_id,
                    "type": MarketType.OVER_UNDER.value,
                    "title": get_over_under_type(event.sport),
                }
            ])

        return events_data, markets_data

create_events = CreateEvents() 