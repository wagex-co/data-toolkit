import requests
from typing import Dict, Optional, List
from urllib.parse import quote
from tabulate import tabulate
from src.config.settings import settings
import time

class SportsDBAPI:
    """Utility class for interacting with TheSportsDB API"""
    
    BASE_URL = "https://www.thesportsdb.com/api/v1/json"
    BASE_URL_V2 = "https://www.thesportsdb.com/api/v2/json"
    
    def __init__(self):
        """
        Initialize the API client
        Args:
            api_key (str): API key for TheSportsDB. Defaults to "3" (free tier test key)
        """
        self.api_key = settings.SPORTSDB_API_KEY
        # For V2 API, we use the same key but as a header instead of in the URL
        self.v2_api_key = settings.SPORTSDB_API_KEY

    def _make_request(self, endpoint: str, v2: bool = False) -> Dict:
        """
        Make a GET request to the API
        
        Args:
            endpoint (str): API endpoint to call
            v2 (bool): Whether to use the v2 API endpoint. Note: V2 API requires a paid Patreon
                subscription and the API key must be sent in the X-API-KEY header.
            
        Returns:
            Dict: JSON response from the API
        """
        RETRY_LIMIT = 3
        RETRY_DELAY = 60
        
        headers = {}
        if v2:
            base_url = self.BASE_URL_V2
            url = f"{base_url}/{endpoint}"
            # For V2 API, the key is sent in the header
            headers["X-API-KEY"] = self.v2_api_key
        else:
            base_url = self.BASE_URL
            url = f"{base_url}/{self.api_key}/{endpoint}"

        
        while RETRY_LIMIT > 0:
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                RETRY_LIMIT -= 1
                time.sleep(RETRY_DELAY)
                final_error = e

        raise Exception(f"Failed to make request to {url} after {RETRY_LIMIT} retries: {final_error}")


    
    def search_team(self, team_name: str) -> Dict:
        """
        Search for a team by name
        
        Args:
            team_name (str): Name of the team to search for
            
        Returns:
            Dict: Team information
        """
        endpoint = f"searchteams.php?t={quote(team_name)}"
        return self._make_request(endpoint)
    
    def search_player(self, player_name: str) -> Dict:
        """
        Search for a player by name
        
        Args:
            player_name (str): Name of the player to search for
            
        Returns:
            Dict: Player information
        """
        # Replace spaces with underscores as per API documentation
        player_name = player_name.replace(" ", "_")
        endpoint = f"searchplayers.php?p={quote(player_name)}"
        return self._make_request(endpoint)
    
    def get_league_teams(self, league_name: str) -> Dict:
        """
        Get all teams in a league
        
        Args:
            league_name (str): Name of the league
            
        Returns:
            Dict: Teams in the league
        """
        endpoint = f"search_all_teams.php?l={quote(league_name)}"
        return self._make_request(endpoint)
    
    def get_team_next_events(self, team_id: str) -> Dict:
        """
        Get next 5 events for a team (Note: Premium feature)
        
        Args:
            team_id (str): ID of the team
            
        Returns:
            Dict: Upcoming events for the team
        """
        endpoint = f"eventsnext.php?id={team_id}"
        return self._make_request(endpoint)
        
    def search_event(self, event_name: str, season: Optional[str] = None) -> Dict:
        """
        Search for an event by name
        
        Args:
            event_name (str): Name of the event
            season (str, optional): Season to search in (e.g., "2016-2017")
            
        Returns:
            Dict: Event information
        """
        event_name = event_name.replace(" ", "_")
        if season:
            endpoint = f"searchevents.php?e={quote(event_name)}&s={season}"
        else:
            endpoint = f"searchevents.php?e={quote(event_name)}"
        return self._make_request(endpoint)
    
    def get_league_seasons(self, league_id: str) -> Dict:
        """
        Get all seasons for a league
        
        Args:
            league_id (str): ID of the league
            
        Returns:
            Dict: Seasons information
        """
        endpoint = f"search_all_seasons.php?id={league_id}"
        return self._make_request(endpoint)
    
    def get_league_table(self, league_id: str, season: str) -> Dict:
        """
        Get league table/standings for a specific season
        
        Args:
            league_id (str): ID of the league
            season (str): Season (e.g., "2020-2021")
            
        Returns:
            Dict: League table information
        """
        endpoint = f"lookuptable.php?l={league_id}&s={season}"
        return self._make_request(endpoint)
    
    def lookup_all_players(self, team_id: str) -> Dict:
        """
        Get all players in a team
        
        Args:
            team_id (str): ID of the team
            
        Returns:
            Dict: Information about all players in the team
        """
        endpoint = f"lookup_all_players.php?id={team_id}"
        return self._make_request(endpoint)
    
    def lookup_event(self, event_id: str) -> Dict:
        """
        Get details for a specific event by ID
        
        Args:
            event_id (str): ID of the event
            
        Returns:
            Dict: Detailed information about the event
        """
        endpoint = f"lookupevent.php?id={event_id}"
        return self._make_request(endpoint)
    
    def lookup_event_stats(self, event_id: str) -> Dict:
        """
        Get statistics for a specific event by ID
        
        Args:
            event_id (str): ID of the event
            
        Returns:
            Dict: Statistical information for the event
        """
        endpoint = f"lookupeventstats.php?id={event_id}"
        return self._make_request(endpoint)
    
    def lookup_event_lineup(self, event_id: str) -> Dict:
        """
        Get lineup details for a specific event by ID
        
        Args:
            event_id (str): ID of the event
            
        Returns:
            Dict: Lineup information for the event
        """
        endpoint = f"lookuplineup.php?id={event_id}"
        return self._make_request(endpoint)
    
    def lookup_event_timeline(self, event_id: str) -> Dict:
        """
        Get timeline information for a specific event by ID
        
        Args:
            event_id (str): ID of the event
            
        Returns:
            Dict: Timeline information for the event
        """
        endpoint = f"lookuptimeline.php?id={event_id}"
        return self._make_request(endpoint)
    
    def lookup_event_results(self, event_id: str) -> Dict:
        """
        Get results for a specific event by ID
        
        Args:
            event_id (str): ID of the event
            
        Returns:
            Dict: Results information for the event
        """
        endpoint = f"eventresults.php?id={event_id}"
        return self._make_request(endpoint)
    
    def get_past_league_events(self, league_id: str) -> Dict:
        """
        Get the last 15 events for a league by ID
        
        Args:
            league_id (str): ID of the league
            
        Returns:
            Dict: Past 15 events for the league
        """
        endpoint = f"eventspastleague.php?id={league_id}"
        return self._make_request(endpoint)
    
    def get_season_events(self, league_id: str, season: str) -> Dict:
        """
        Get all events in a specific league by season
        (Free tier limited to 100 events)
        
        Args:
            league_id (str): ID of the league
            season (str): Season (e.g., "2014-2015")
            
        Returns:
            Dict: All events for the league in the specified season
        """
        endpoint = f"eventsseason.php?id={league_id}&s={season}"
        return self._make_request(endpoint)
    
    def list_seasons(self, league_id: str) -> Dict:
        """
        List all seasons for a league (V2 API)
        
        Args:
            league_id (str): ID of the league
            
        Returns:
            Dict: All seasons for the league
        """
        endpoint = f"list/seasons/{league_id}"
        return self._make_request(endpoint, v2=True)
    
    def list_season_posters(self, league_id: str) -> Dict:
        """
        List season posters for a league (V2 API)
        
        Args:
            league_id (str): ID of the league
            
        Returns:
            Dict: Season posters for the league
        """
        endpoint = f"list/seasonposters/{league_id}"
        return self._make_request(endpoint, v2=True)
    
    def list_players_by_team_id(self, team_id: str) -> Dict:
        """
        List all players in a team by team ID (V2 API)
        
        Args:
            team_id (str): ID of the team
            
        Returns:
            Dict: All players in the team
        """
        endpoint = f"list/players/{team_id}"
        return self._make_request(endpoint, v2=True)
    
    def list_players_by_team_name(self, team_name: str) -> Dict:
        """
        List all players in a team by team name (V2 API)
        
        Args:
            team_name (str): Name of the team (replace spaces with underscores)
            
        Returns:
            Dict: All players in the team
        """
        # Replace spaces with underscores if not already done
        team_name = team_name.replace(" ", "_")
        endpoint = f"list/players/{team_name}"
        return self._make_request(endpoint, v2=True)
    
    def list_teams_by_league_id(self, league_id: str) -> Dict:
        """
        List all teams in a league by league ID (V2 API)
        
        Args:
            league_id (str): ID of the league
            
        Returns:
            Dict: All teams in the league
        """
        endpoint = f"list/teams/{league_id}"
        return self._make_request(endpoint, v2=True)
    
    def list_teams_by_league_name(self, league_name: str) -> Dict:
        """
        List all teams in a league by league name (V2 API)
        
        Args:
            league_name (str): Name of the league (replace spaces with underscores)
            
        Returns:
            Dict: All teams in the league
        """
        # Replace spaces with underscores if not already done
        league_name = league_name.replace(" ", "_")
        endpoint = f"list/teams/{league_name}"
        return self._make_request(endpoint, v2=True)
    
    def schedule_next_league(self, league_id: str) -> Dict:
        """
        Get next events schedule for a league (V2 API)
        
        Args:
            league_id (str): ID of the league
            
        Returns:
            Dict: Next events for the league
        """
        endpoint = f"schedule/next/league/{league_id}"
        return self._make_request(endpoint, v2=True)
    
    def schedule_previous_league(self, league_id: str) -> Dict:
        """
        Get previous events schedule for a league (V2 API)
        
        Args:
            league_id (str): ID of the league
            
        Returns:
            Dict: Previous events for the league
        """
        endpoint = f"schedule/previous/league/{league_id}"
        return self._make_request(endpoint, v2=True)
    
    def schedule_next_team(self, team_id: str) -> Dict:
        """
        Get next events schedule for a team (V2 API)
        
        Args:
            team_id (str): ID of the team
            
        Returns:
            Dict: Next events for the team
        """
        endpoint = f"schedule/next/team/{team_id}"
        return self._make_request(endpoint, v2=True)
    
    def schedule_previous_team(self, team_id: str) -> Dict:
        """
        Get previous events schedule for a team (V2 API)
        
        Args:
            team_id (str): ID of the team
            
        Returns:
            Dict: Previous events for the team
        """
        endpoint = f"schedule/previous/team/{team_id}"
        return self._make_request(endpoint, v2=True)
    
    def schedule_full_team(self, team_id: str) -> Dict:
        """
        Get full events schedule for a team (V2 API)
        
        Args:
            team_id (str): ID of the team
            
        Returns:
            Dict: Full schedule for the team
        """
        endpoint = f"schedule/full/team/{team_id}"
        return self._make_request(endpoint, v2=True)
    
    def schedule_league_season(self, league_id: str, season: str) -> Dict:
        """
        Get full season schedule for a league (V2 API)
        
        Args:
            league_id (str): ID of the league
            season (str): Season (e.g., "2023-2024")
            
        Returns:
            Dict: Full season schedule for the league
        """
        endpoint = f"schedule/league/{league_id}/{season}"
        return self._make_request(endpoint, v2=True)
    
    def _format_table(self, data: Dict, keys: List[str]) -> str:
        """
        Format dictionary data into a readable table
        
        Args:
            data (Dict): Response data from API
            keys (List[str]): Keys to extract from each item
            
        Returns:
            str: Formatted table string
        """
        if not data or not isinstance(data, dict):
            return "No data found"
            
        # Most API responses store main data in first key
        main_key = list(data.keys())[0]
        items = data[main_key]
        
        if not items:
            return "No results found"
            
        # Extract specified fields from each item
        table_data = [[item.get(k, '') for k in keys] for item in items]
        return tabulate(table_data, headers=keys, tablefmt='grid')

if __name__ == "__main__":
    api = SportsDBAPI()

    # get lineup for each event in the schedule
    vals = list((event['strEvent'], event['idEvent']) for event in api.schedule_previous_team("133664")['schedule'])
    for val in vals:
        print(val)
        try:
            # print(list(player['strPlayer'] for player in api.lookup_event_lineup(val[1])['lineup']))
            # print(api.lookup_event_stats(val[1])['eventstats'])
            # # get stats
            # stats = api.lookup_event_stats(val[1])['eventstats']
            # print(list((stat['strStat'], stat['intHome'], stat['intAway']) for stat in stats))
            ## Event Details
            # event_details = api.lookup_event(val[1])['events'][0]
            # print(event_details)
            # event_results = api.lookup_event_results(val[1])
            # print(event_results)
            #event timeline
            event_timeline = api.lookup_event_timeline(val[1])
            print(event_timeline)
        except Exception as e:
            print(e)

    # get lineup for most recent event for toronto maple leafs
    # print(list(player['strPlayer'] for player in api.lookup_event_lineup("2090600")['lineup']))
    # stats = api.lookup_event_stats("2090600")['eventstats']
    # print(list((stat['strStat'], stat['intHome'], stat['intAway']) for stat in stats))
    # print(stats)
