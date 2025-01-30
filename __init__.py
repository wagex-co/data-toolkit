from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
import re
import json
import random
import asyncio
import aiohttp
from functools import lru_cache
import backoff  # You'll need to pip install backoff

SPORT_DICT = {
    "NBA": "nba-basketball",
    "NFL": "nfl-football",
    "NHL": "nhl-hockey",
    "MLB": "mlb-baseball",
    "NCAAB": "ncaa-basketball",
    "EPL": "english-premier-league",
    "UCL": "champions-league"
}

@dataclass
class Team:
    full_name: str
    display_name: str
    short_name: str
    rank: Optional[int]

@dataclass
class Game:
    date: str
    status: str
    home_team: Team
    away_team: Team
    home_score: int
    away_score: int
    home_spread: Dict[str, float]
    home_spread_odds: Dict[str, int]
    away_spread: Dict[str, float]
    away_spread_odds: Dict[str, int]
    under_odds: Dict[str, int]
    over_odds: Dict[str, int]
    total: Dict[str, float]
    home_ml: Dict[str, int]
    away_ml: Dict[str, int]

    @classmethod
    def from_event(cls, event: dict, line_type: str) -> 'Game':
        spreads = event['spreads']
        totals = event['totals']
        moneylines = event['moneylines']
        
        game_view = spreads['gameView']
        
        return cls(
            date=game_view['startDate'],
            status=game_view['gameStatusText'],
            home_team=Team(
                full_name=game_view['homeTeam']['fullName'],
                display_name=game_view['homeTeam']['displayName'],
                short_name=game_view['homeTeam']['shortName'],
                rank=game_view['homeTeam']['rank']
            ),
            away_team=Team(
                full_name=game_view['awayTeam']['fullName'],
                display_name=game_view['awayTeam']['displayName'],
                short_name=game_view['awayTeam']['shortName'],
                rank=game_view['awayTeam']['rank']
            ),
            home_score=game_view['homeTeamScore'],
            away_score=game_view['awayTeamScore'],
            home_spread={line['sportsbook']: line[line_type]['homeSpread'] for line in spreads['oddsViews'] if line},
            home_spread_odds={line['sportsbook']: line[line_type]['homeOdds'] for line in spreads['oddsViews'] if line},
            away_spread={line['sportsbook']: line[line_type]['awaySpread'] for line in spreads['oddsViews'] if line},
            away_spread_odds={line['sportsbook']: line[line_type]['awayOdds'] for line in spreads['oddsViews'] if line},
            under_odds={line['sportsbook']: line[line_type]['underOdds'] for line in totals.get('oddsViews', []) if line},
            over_odds={line['sportsbook']: line[line_type]['overOdds'] for line in totals.get('oddsViews', []) if line},
            total={line['sportsbook']: line[line_type]['total'] for line in totals.get('oddsViews', []) if line},
            home_ml={line['sportsbook']: line[line_type]['homeOdds'] for line in moneylines.get('oddsViews', []) if line},
            away_ml={line['sportsbook']: line[line_type]['awayOdds'] for line in moneylines.get('oddsViews', []) if line}
        )

class Scoreboard:
    def __init__(self, sport='NBA', days_ahead=1, current_line=True, delay=False):
        self.games: List[Game] = []
        date = (datetime.today() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        self.date = date
        self.delay = delay
        self.current_line = current_line
        self.sport = sport
        self.session = requests.Session()  # Reuse session for better performance
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        ]
        try:
            self.scrape_games()
        except Exception as e:
            print(f"An error occurred: {e}")

    def __repr__(self) -> str:
        return f"Scoreboard(games={self.games})"

    @lru_cache(maxsize=32)
    def _get_build_id(self, initial_url: str) -> str:
        """Cache and retrieve build_id to avoid repeated requests"""
        response = self.session.get(initial_url)
        json_data = json.loads(re.findall('__NEXT_DATA__" type="application/json">(.*?)</script>', 
                                        response.text)[0])
        return json_data['buildId']

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=3)
    def _fetch_data(self, url: str) -> dict:
        """Improved fetch with retry logic and session reuse"""
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
        
        response = self.session.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    async def _fetch_all_data(self, base_url: str, date: str) -> Tuple[dict, dict, dict]:
        """Fetch all data concurrently"""
        async with aiohttp.ClientSession() as session:
            tasks = [
                self._async_fetch(session, f"{base_url}.json?league={SPORT_DICT[self.sport]}&date={date}"),
                self._async_fetch(session, f"{base_url}/money-line/full-game.json?league={SPORT_DICT[self.sport]}&oddsType=money-line&oddsScope=full-game&date={date}"),
                self._async_fetch(session, f"{base_url}/totals/full-game.json?league={SPORT_DICT[self.sport]}&oddsType=totals&oddsScope=full-game&date={date}")
            ]
            print("First url:", f"{base_url}.json?league={SPORT_DICT[self.sport]}&date={date}")
            print("totals url:", f"{base_url}/totals/full-game.json?league={SPORT_DICT[self.sport]}&oddsType=totals&oddsScope=full-game&date={date}")
            spreads, moneylines, totals = await asyncio.gather(*tasks)
            return spreads, moneylines, totals

    async def _async_fetch(self, session: aiohttp.ClientSession, url: str) -> dict:
        """Helper method for async fetching"""
        headers = {'User-Agent': random.choice(self.user_agents)}
        async with session.get(url, headers=headers) as response:
            return await response.json()

    def _process_game_rows(self, json_data: dict) -> Dict[str, dict]:
        game_list = []
        for item in json_data['pageProps']['oddsTables']:
            print(item)
            game_list.extend(item['oddsTableModel']['gameRows'])
        return {g['gameView']['gameId']: g for g in game_list}

    def scrape_games(self):
        date = self.date or (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        line_type = 'currentLine' if self.current_line else 'openingLine'

        initial_url = f"https://www.sportsbookreview.com/betting-odds/{SPORT_DICT[self.sport]}/?date={date}"
        build_id = self._get_build_id(initial_url)
        base_url = f"https://www.sportsbookreview.com/_next/data/{build_id}/betting-odds/{SPORT_DICT[self.sport]}"

        # Use asyncio to fetch data concurrently
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        spreads_data, moneylines_data, totals_data = loop.run_until_complete(
            self._fetch_all_data(base_url, date)
        )
        loop.close()

        spreads = self._process_game_rows(spreads_data)
        moneylines = self._process_game_rows(moneylines_data)
        totals = self._process_game_rows(totals_data)

        all_stats = {
            game_id: {'spreads': spreads[game_id], 'moneylines': moneylines[game_id], 'totals': totals[game_id]}
            for game_id in spreads.keys()
        }

        self.games = [Game.from_event(event, line_type) for event in all_stats.values()]

    def get_totals(self, home_team: Optional[str] = None, away_team: Optional[str] = None) -> Dict[str, float]:
        def process_total(totals_dict: Dict[str, float]) -> Optional[float]:
            if not totals_dict:
                return None

            half_point = next((total for total in totals_dict.values() if total and total % 1 == 0.5), None)
            if half_point is not None:
                return half_point

            first_valid = next((total for total in totals_dict.values() if total), None)
            return round(first_valid * 2) / 2 if first_valid else None

        if not home_team and not away_team:
            return {f"{game.home_team.full_name}vs{game.away_team.full_name}": process_total(game.total) 
                    for game in self.games}

        for game in self.games:
            if (game.home_team.full_name == home_team and game.away_team.full_name == away_team):
                return {f"{home_team}vs{away_team}": process_total(game.total)}
            elif (game.home_team.full_name == away_team and game.away_team.full_name == home_team):
                return {f"{away_team}vs{home_team}": process_total(game.total)}
        return {}

    def get_ml(self, home_team: Optional[str] = None, away_team: Optional[str] = None) -> Dict[str, Dict[str, int]]:
        def process_ml(home_ml: Dict[str, int], away_ml: Dict[str, int]) -> Dict[str, int]:
            if not home_ml or not away_ml:
                return {}
            return {
                'home': next((odds for odds in home_ml.values() if odds), None),
                'away': next((odds for odds in away_ml.values() if odds), None)
            }

        if not home_team and not away_team:
            return {f"{game.home_team.full_name}vs{game.away_team.full_name}": process_ml(game.home_ml, game.away_ml) 
                    for game in self.games}

        for game in self.games:
            if (game.home_team.full_name == home_team and game.away_team.full_name == away_team):
                return {f"{home_team}vs{away_team}": process_ml(game.home_ml, game.away_ml)}
            elif (game.home_team.full_name == away_team and game.away_team.full_name == home_team):
                return {f"{away_team}vs{home_team}": process_ml(game.away_ml, game.home_ml)}  
        return {}
    
    def get_scores(self, home_team: Optional[str] = None, away_team: Optional[str] = None):
        """
        Only works post game I think? DOesn't seem to be returning scores during game for soccer... Maybe it works for other sports?
        """
        if not home_team and not away_team:
            return {f"{game.home_team.full_name}vs{game.away_team.full_name}": (game.home_score, game.away_score) for game in self.games}
        for game in self.games:
            if (game.home_team.full_name == home_team and game.away_team.full_name == away_team):
                return {f"{home_team}vs{away_team}": (game.home_score, game.away_score)}
            elif (game.home_team.full_name == away_team and game.away_team.full_name == home_team):
                return {f"{away_team}vs{home_team}": (game.away_score, game.home_score)}
        return {}


def main():
    # Get tomorrow's totals for NBA
    print("\nNBA Tomorrow's Game Totals:")
    nba_board = Scoreboard(sport="NBA", days_ahead=0)
    print(nba_board.get_totals())
    
    # Get tomorrow's totals for NHL
    print("\nNHL Tomorrow's Game Totals:")
    nhl_board = Scoreboard(sport="NHL", days_ahead=0)
    print(nhl_board.get_totals())

if __name__ == "__main__":
    main()
