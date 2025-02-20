import requests
from typing import Dict
import time
import json
from config.settings import settings

def get_teams_by_league(league_name: str, league_id: str, api_key: str) -> list:
    """
    Fetch teams for a specific league from TheSportsDB API
    """
    base_url = "https://www.thesportsdb.com/api/v1/json"
    endpoint = f"{base_url}/{api_key}/lookup_all_teams.php?id={league_id}"
    
    try:
        response = requests.get(endpoint)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        data = response.json()
        if not data or 'teams' not in data or not data['teams']:
            print(f"No teams found for {league_name}")
            return []
            
        return [(
            team['strTeam'],
            team['idTeam'],
            team.get('strTeamAlternate', 'N/A').split(','), 
            team.get('strTeamShort', 'N/A'),
            team.get('strBadge', 'N/A') 
        ) for team in data['teams']]
        
    except requests.RequestException as e:
        print(f"Error fetching data for {league_name}: {str(e)}")
        return []
    except KeyError as e:
        print(f"Unexpected data format for {league_name}: {str(e)}")
        return []

def get_league_details(league_id: str, api_key: str) -> Dict:
    """
    Fetch detailed information for a specific league from TheSportsDB API
    """
    base_url = "https://www.thesportsdb.com/api/v1/json"
    endpoint = f"{base_url}/{api_key}/lookupleague.php?id={league_id}"
    
    try:
        response = requests.get(endpoint)
        response.raise_for_status()
        
        data = response.json()
        if not data or 'leagues' not in data or not data['leagues']:
            print(f"No league found for ID {league_id}")
            return {}
            
        league = data['leagues'][0]  # Get first league from the response
        return {
            'name': league.get('strLeague', 'N/A'),
            'sportdb_id': league.get('idLeague', 'N/A'),
            'alternate_name': league.get('strLeagueAlternate', 'N/A'),
            'sport': league.get('strSport', 'N/A'),
            'country': league.get('strCountry', 'N/A'),
            'website': league.get('strWebsite', 'N/A'),
            'facebook': league.get('strFacebook', 'N/A'),
            'twitter': league.get('strTwitter', 'N/A'),
            'youtube': league.get('strYoutube', 'N/A'),
            'banner': league.get('strBanner', 'N/A'),
            'badge': league.get('strBadge', 'N/A'),
            'logo': league.get('strLogo', 'N/A'),
            'trophy': league.get('strTrophy', 'N/A'),
            'formed_year': league.get('intFormedYear', 'N/A'),
            'gender': league.get('strGender', 'N/A'),
            'strNaming': league.get('strNaming', 'N/A'),
        }
        
    except requests.RequestException as e:
        print(f"Error fetching league data: {str(e)}")
        return {}
    except KeyError as e:
        print(f"Unexpected data format: {str(e)}")
        return {}

def main():
    # Get API key from environment variable
    api_key = settings.SPORTSDB_API_KEY
    if not api_key:
        print("Error: SPORTSDB_API_KEY environment variable not set")
        return

    # The final data is organized by league (each league is a top-level key)
    final_data = {}

    # Process each league defined in LEAGUE_IDS
    for league_name, league_id in settings.LEAGUE_IDS.items():
        print(f"\nFetching data for {league_name}...")
        time.sleep(1)

        # Get league details and teams for the given league
        league_details = get_league_details(league_id, api_key)
        teams = get_teams_by_league(league_name, league_id, api_key)

        # Add an ESPN mapping for the league, if applicable
        league_details["espns_name"] = settings.ESPN_LEAGUE_NAMES.get(league_name, league_details.get("name", league_name))

        # Create a block for this league with its league_data first
        league_block = {"league_data": league_details}

        # Now, add each team under the league block
        for team_name, team_id, team_alternate, team_short, team_badge in teams:
            team_data = {
                "id": team_id,
                "alternate_names": team_alternate,
                "short_name": team_short,
                "badge_url": team_badge,
                "espns_name": team_name
            }
            league_block[team_name] = team_data

        # Use the league's name as the key in the final JSON
        final_data[league_name] = league_block

    # Output the JSON with pretty formatting
    with open('leagues_data.json', 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=2)
    print(json.dumps(final_data, indent=2))

if __name__ == "__main__":
    main()
