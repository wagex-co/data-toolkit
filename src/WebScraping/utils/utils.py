from typing import Optional, Tuple
import difflib
from pathlib import Path
import sys
import json

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))
from src.config.settings import settings

def fuzzy_match_team_name(espn_name: str, league_data: dict, threshold: float = 0.8) -> Optional[Tuple[str, float]]:
    """
    Attempt to find a fuzzy match for an ESPN team name in the league data.
    
    Args:
        espn_name (str): The ESPN team name to match
        league_data (dict): The league data containing team mappings
        threshold (float): Minimum similarity score required for a match (0.0 to 1.0)
        
    Returns:
        Optional[Tuple[str, float]]: The matched team name and similarity score, or None if no match above threshold
    """
    if "teams" not in league_data:
        return None
    
    # First check for exact match with espns_name
    for team_name, team_info in league_data["teams"].items():
        if "espns_name" in team_info and team_info["espns_name"] == espn_name:
            return team_name, 1.0
    
    # Check for substring match with team names and their espns_name
    for team_name, team_info in league_data["teams"].items():
        # Check the main team name
        if espn_name.lower() in team_name.lower() or team_name.lower() in espn_name.lower():
            # Make sure it's a substantial match (avoid matching "United" to any team with "United")
            if len(espn_name) > 3 and len(team_name) > 3:
                return team_name, 0.95
        
        # Check the ESPN name if available
        if "espns_name" in team_info:
            espns_name = team_info["espns_name"]
            if espn_name.lower() in espns_name.lower() or espns_name.lower() in espn_name.lower():
                if len(espn_name) > 3 and len(espns_name) > 3:
                    return team_name, 0.95
    
    # Check alternate names
    for team_name, team_info in league_data["teams"].items():
        if "alternate_names" in team_info:
            for alt_name in team_info["alternate_names"]:
                if espn_name.lower() in alt_name.lower() or alt_name.lower() in espn_name.lower():
                    if len(espn_name) > 3 and len(alt_name) > 3:
                        return team_name, 0.9
    
    # Build a list of all possible names for fuzzy matching
    all_names = []
    for team_name, team_info in league_data["teams"].items():
        all_names.append(team_name)
        if "espns_name" in team_info:
            all_names.append(team_info["espns_name"])
        if "alternate_names" in team_info:
            all_names.extend(team_info["alternate_names"])
    
    # Remove duplicates
    all_names = list(set(all_names))
    
    # Try difflib's fuzzy matching as a last resort
    matches = difflib.get_close_matches(espn_name, all_names, n=1, cutoff=threshold)
    
    if matches:
        # Calculate similarity score
        similarity = difflib.SequenceMatcher(None, espn_name.lower(), matches[0].lower()).ratio()
        
        # Find the team this matched name belongs to
        for team_name, team_info in league_data["teams"].items():
            if matches[0] == team_name:
                return team_name, similarity
            if "espns_name" in team_info and matches[0] == team_info["espns_name"]:
                return team_name, similarity
            if "alternate_names" in team_info and matches[0] in team_info["alternate_names"]:
                return team_name, similarity
    
    return None

def map_team_name(espn_name: str, league: str):
    """
    Map ESPN team names to our stored names from the espn names.
    
    Args:
        espn_name (str): The ESPN team name to map
        league (str): The league name
        
    Returns:
        str: The mapped team name or the original ESPN name if no mapping is found
    """
    if league in settings.LEAGUE_DATA:
        league_data = settings.LEAGUE_DATA[league]
        
        # Try fuzzy matching (which now includes exact matching as first priority)
        fuzzy_match = fuzzy_match_team_name(espn_name, league_data)
        if fuzzy_match:
            matched_name, confidence = fuzzy_match
            if confidence < 1.0:  # Only log if it's not an exact match
                print(f"Matched '{espn_name}' to '{matched_name}' with confidence {confidence:.2f}")
                
                if confidence > 0.899 and "teams" in league_data and matched_name in league_data["teams"]:
                    if "espns_name" not in league_data["teams"][matched_name] or league_data["teams"][matched_name]["espns_name"] != espn_name:
                        print(f"Updating espns_name for '{matched_name}' to '{espn_name}'")
                        settings.LEAGUE_DATA[league]["teams"][matched_name]["espns_name"] = espn_name
                        
                        try:
                            league_data_file_path = 'DATA_MAIN/league_data.json'
                            with open(league_data_file_path, 'w', encoding='utf-8') as f:
                                json.dump(settings.LEAGUE_DATA, f, indent=4)
                            print(f"Successfully updated {league_data_file_path}")
                        except Exception as e:
                            print(f"Error updating league data file: {e}")
                
            return matched_name
        else:
            print(f"No mapping found for {espn_name} in {league}")
            return espn_name
    else:
        print(f"No mapping found for {league}")
        return espn_name