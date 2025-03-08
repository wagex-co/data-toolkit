from typing import Dict, Any, List, Tuple
import json
import logging

from src.WebScraping.utils.sportsdb_utilities import SportsDBAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def settle_soccer_game_props(event_id: str) -> Dict[str, Any]:
    """
    Settle all game props for a soccer match based on TheSportsDB event data.
    
    Args:
        event_id (str): TheSportsDB event ID
        
    Returns:
        Dict[str, Any]: Dictionary with settlement results for all game props
    """
    api = SportsDBAPI()
    
    event_stats = api.lookup_event_stats(event_id)
    event_timeline = api.lookup_event_timeline(event_id)
    event_details = api.lookup_event(event_id)
   
    if not event_stats or not event_timeline or not event_details:
        raise ValueError(f"Could not retrieve complete data for event {event_id}")
    try:
        home_team = event_details['events'][0]['strHomeTeam']
        away_team = event_details['events'][0]['strAwayTeam']
        home_score = int(event_details['events'][0]['intHomeScore'] or 0)
        away_score = int(event_details['events'][0]['intAwayScore'] or 0)
        stats = _extract_team_stats(event_stats)
        timeline, home_half_score, away_half_score = _organize_timeline(event_timeline, home_team, away_team)

    except (KeyError, IndexError, TypeError) as e:
        raise ValueError(f"Error processing event data: {e}")
    
    results = {}
    
    results["goalTotals"] = _settle_goal_totals(home_score, away_score, stats)
    results["halfTimeResults"] = _settle_halftime_results(home_half_score, away_half_score)
    results["bothTeamsToScore"] = home_score > 0 and away_score > 0
    results["doubleChance"] = _settle_double_chance(home_score, away_score)
    results["correctScore"] = f"{home_score}-{away_score}"
    results["winningMargin"] = _settle_winning_margin(home_score, away_score)
    results["halfWithMostGoals"] = _settle_half_with_most_goals(home_score, away_score, home_half_score, away_half_score)
    results["oddEvenGoals"] = "odd" if (home_score + away_score) % 2 == 1 else "even"
    results["teamToScoreFirst"] = _settle_team_to_score_first(timeline)
    results["teamToScoreLast"] = _settle_team_to_score_last(timeline)
    results["cornerTotals"] = _settle_corner_totals(stats)
    results["cardTotals"] = _settle_card_totals(stats, timeline)
    results["foulTotals"] = _settle_foul_totals(stats)
    results["redCard"] = _has_red_card(timeline)
    results["ownGoal"] = _has_own_goal(timeline)
    results["goalTimings"] = _settle_goal_timings(timeline)
    results["halftimeFulltime"] = _settle_halftime_fulltime(home_half_score, away_half_score, home_score, away_score)
    results["shotsTotals"] = _settle_shots_totals(stats)
    results["offsideTotals"] = _settle_offside_totals(stats)
    results["goalTiming"] = _settle_goal_timing_intervals(timeline)
    
    return results



def _extract_team_stats(event_stats: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
    """Extract and organize team statistics from event_stats response"""
    stats = {"home": {}, "away": {}}
    
    # Handle different API response structures
    stats_list = None
    if 'eventstats' in event_stats:
        stats_list = event_stats['eventstats']
    elif 'statistics' in event_stats:
        stats_list = event_stats['statistics']
    
    if not stats_list:
        return stats
    
    for stat in stats_list:
        try:
            # Keep original stat name for direct lookup
            original_name = stat.get('strStat', '')
            # Also create a normalized key name for programmatic access
            type_name = original_name.lower().replace(' ', '_')
            home_value = _parse_stat_value(stat.get('intHome', '0'))
            away_value = _parse_stat_value(stat.get('intAway', '0'))
            
            # Store both the normalized and original key names
            stats['home'][type_name] = home_value
            stats['away'][type_name] = away_value
            stats['home'][original_name] = home_value
            stats['away'][original_name] = away_value
        except (ValueError, KeyError) as e:
            logger.warning(f"Error processing stat {stat.get('strStat', 'unknown')}: {e}")
            continue
    
    return stats

def _parse_stat_value(value: str) -> int:
    """Parse statistical value, handling empty strings and non-numeric values"""
    if not value or not value.strip():
        return 0
    try:
        return int(value)
    except ValueError:
        try:
            return int(float(value))
        except ValueError:
            return 0

def _organize_timeline(event_timeline: Dict[str, Any], home_team: str, away_team: str) -> Tuple[List[Dict[str, Any]], int, int]:
    """Organize timeline events chronologically with additional metadata"""
    timeline_events = []
    home_half_score = 0
    away_half_score = 0
    
    if not event_timeline.get('timeline'):
        return timeline_events, home_half_score, away_half_score
    
    for event in event_timeline['timeline']:
        try:
            event_type = event.get('strTimeline', '').lower()
            event_detail = event.get('strTimelineDetail', '').lower()
            team_name = event.get('strTeam', '')
            is_home = team_name == home_team
            is_away = team_name == away_team
            
            if not (is_home or is_away):
                continue
                
            team = "home" if is_home else "away"
            minute = int(event.get('intTime', 0))
            
            if not event_type:
                continue
                
            # Map event types to standardized types for settlement functions
            standard_type = event_type
            if event_type == 'goal':
                standard_type = 'goal'
            elif event_type == 'card':
                if 'yellow' in event_detail:
                    standard_type = 'yellow card'
                elif 'red' in event_detail:
                    standard_type = 'red card'
                else:
                    standard_type = 'card'  # generic card if not specified
            
            timeline_event = {
                "type": standard_type,
                "detail": event_detail,
                "team": team,
                "minute": minute,
                "player": event.get('strPlayer', ''),
                "assist": event.get('strAssist', '')
            }
            
            if standard_type == 'goal':
                if is_home:
                    if minute <= 45:
                        home_half_score += 1
                else:
                    if minute <= 45:
                        away_half_score += 1
                        
            timeline_events.append(timeline_event)
        except Exception as e:
            print(f"Error processing timeline event: {e}")
            continue
    timeline_events.sort(key=lambda x: x['minute'])
    return timeline_events, home_half_score, away_half_score

def _settle_goal_totals(home_score: int, away_score: int, stats: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
    """Settle goal totals markets"""
    return {
        "exactGoals": home_score + away_score,
        "teamTotals": {
            "home": float(home_score),
            "away": float(away_score)
        }
    }

def _settle_halftime_results(home_half_score: int, away_half_score: int) -> Dict[str, bool]:
    """Settle halftime results markets"""
    return {
        "homeWin": home_half_score > away_half_score,
        "awayWin": away_half_score > home_half_score
    }

def _settle_double_chance(home_score: int, away_score: int) -> List[str]:
    """Settle double chance markets"""
    results = []
    
    if home_score >= away_score:  # Home win or draw
        results.append("homeOrDraw")
    
    if away_score >= home_score:  # Away win or draw
        results.append("drawOrAway")
    
    if home_score != away_score:  # Not a draw
        results.append("homeOrAway")
        
    return results

def _settle_winning_margin(home_score: int, away_score: int) -> int:
    """Settle winning margin market"""
    return abs(home_score - away_score)

def _settle_half_with_most_goals(home_score: int, away_score: int, 
                               home_half_score: int, away_half_score: int) -> str:
    """Settle half with most goals market"""
    first_half_goals = home_half_score + away_half_score
    second_half_goals = (home_score + away_score) - first_half_goals
    
    if first_half_goals > second_half_goals:
        return "firstHalf"
    elif second_half_goals > first_half_goals:
        return "secondHalf"
    else:
        return "equal"

def _settle_team_to_score_first(timeline: List[Dict[str, Any]]) -> str:
    """Determine which team scored first"""
    for event in timeline:
        if event['type'] == 'goal':
            return event['team']
    return "noGoal"

def _settle_team_to_score_last(timeline: List[Dict[str, Any]]) -> str:
    """Determine which team scored last"""
    for event in reversed(timeline):
        if event['type'] == 'goal':
            return event['team']
    return "noGoal"

def _settle_corner_totals(stats: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
    """Settle corner totals markets"""
    # Try standard normalized keys
    home_corners = stats['home'].get('corner_kicks', 0)
    away_corners = stats['away'].get('corner_kicks', 0)
    
    # If values are 0, try API-specific keys
    if home_corners == 0:
        home_corners = stats['home'].get('Corner Kicks', 0)
    if away_corners == 0:
        away_corners = stats['away'].get('Corner Kicks', 0)
    
    total_corners = home_corners + away_corners
    
    return {
        "overUnder": float(total_corners),
        "exactCorners": total_corners,
        "teamTotals": {
            "home": float(home_corners),
            "away": float(away_corners)
        }
    }

def _settle_card_totals(stats: Dict[str, Dict[str, int]], 
                       timeline: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Settle card totals markets"""
    # Try to get from stats first
    home_yellow = stats['home'].get('yellow_cards', 0)
    away_yellow = stats['away'].get('yellow_cards', 0)
    home_red = stats['home'].get('red_cards', 0)
    away_red = stats['away'].get('red_cards', 0)
    
    # If not in stats or values are zero, try to use the Yellow Cards field from stats
    if home_yellow == 0 and away_yellow == 0:
        home_yellow = stats['home'].get('Yellow Cards', 0)
        away_yellow = stats['away'].get('Yellow Cards', 0)
    
    # If not in stats or values are zero, try to use the Red Cards field from stats
    if home_red == 0 and away_red == 0:
        home_red = stats['home'].get('Red Cards', 0)
        away_red = stats['away'].get('Red Cards', 0)
    
    # If still not found, try to count from timeline
    if home_yellow == 0 and away_yellow == 0 and home_red == 0 and away_red == 0:
        for event in timeline:
            if (event['type'] == 'yellow card' or 'yellow card' in event.get('detail', '').lower()) and event['team'] == 'home':
                home_yellow += 1
            elif (event['type'] == 'yellow card' or 'yellow card' in event.get('detail', '').lower()) and event['team'] == 'away':
                away_yellow += 1
            elif (event['type'] == 'red card' or 'red card' in event.get('detail', '').lower()) and event['team'] == 'home':
                home_red += 1
            elif (event['type'] == 'red card' or 'red card' in event.get('detail', '').lower()) and event['team'] == 'away':
                away_red += 1
    
    home_cards = home_yellow + home_red
    away_cards = away_yellow + away_red
    total_cards = home_cards + away_cards
    
    return {
        "overUnder": float(total_cards),
        "exactCards": total_cards,
        "teamTotals": {
            "home": float(home_cards),
            "away": float(away_cards)
        }
    }

def _settle_foul_totals(stats: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
    """Settle foul totals markets"""
    # Try standard normalized keys
    home_fouls = stats['home'].get('fouls', 0)
    away_fouls = stats['away'].get('fouls', 0)
    
    # If values are 0, try API-specific keys
    if home_fouls == 0:
        home_fouls = stats['home'].get('Fouls', 0)
    if away_fouls == 0:
        away_fouls = stats['away'].get('Fouls', 0)
    
    total_fouls = home_fouls + away_fouls
    
    return {
        "overUnder": float(total_fouls),
        "teamTotals": {
            "home": float(home_fouls),
            "away": float(away_fouls)
        }
    }

def _has_red_card(timeline: List[Dict[str, Any]]) -> bool:
    """Check if there was a red card in the match"""
    for event in timeline:
        if event['type'] == 'red card' or 'red card' in event.get('detail', '').lower():
            return True
    return False

def _has_own_goal(timeline: List[Dict[str, Any]]) -> bool:
    """Check if there was an own goal in the match"""
    for event in timeline:
        if (event['type'] == 'goal' and 'own goal' in event.get('detail', '').lower()) or 'own goal' in event.get('detail', '').lower():
            return True
    return False

def _settle_goal_timings(timeline: List[Dict[str, Any]]) -> Dict[str, bool]:
    """Settle goal timing markets"""
    goal_in_first_10 = False
    goal_in_last_10 = False
    
    for event in timeline:
        # Consider all events as goals if they have a player name and are not cards
        if event['type'] == 'goal':
            minute = event['minute']
            if minute <= 10:
                goal_in_first_10 = True
            if minute >= 80:
                print(f"Goal in last 10 minutes: {event}")
                goal_in_last_10 = True
    
    return {
        "goalIn1st10Minutes": goal_in_first_10,
        "goalInLast10Minutes": goal_in_last_10
    }

def _settle_halftime_fulltime(home_half: int, away_half: int, 
                            home_final: int, away_final: int) -> str:
    """Settle halftime/fulltime result market"""
    ht_result = "home" if home_half > away_half else "away" if away_half > home_half else "draw"
    ft_result = "home" if home_final > away_final else "away" if away_final > home_final else "draw"
    
    return f"{ht_result}{ft_result.capitalize()}"

def _settle_shots_totals(stats: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
    """Settle shots totals markets"""
    # Try standard normalized keys
    home_shots = stats['home'].get('total_shots', 0)
    away_shots = stats['away'].get('total_shots', 0)
    home_shots_on_target = stats['home'].get('shots_on_goal', 0)
    away_shots_on_target = stats['away'].get('shots_on_goal', 0)
    
    # If values are 0, try API-specific keys
    if home_shots == 0:
        home_shots = stats['home'].get('Total Shots', 0)
    if away_shots == 0:
        away_shots = stats['away'].get('Total Shots', 0)
    if home_shots_on_target == 0:
        home_shots_on_target = stats['home'].get('Shots on Goal', 0)
    if away_shots_on_target == 0:
        away_shots_on_target = stats['away'].get('Shots on Goal', 0)
    
    total_shots = home_shots + away_shots
    total_shots_on_target = home_shots_on_target + away_shots_on_target
    
    return {
        "overUnder": float(total_shots),
        "shotsOnTarget": float(total_shots_on_target),
        "teamTotals": {
            "home": float(home_shots),
            "away": float(away_shots)
        }
    }

def _settle_offside_totals(stats: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
    """Settle offside totals markets"""
    # Try standard normalized keys
    home_offsides = stats['home'].get('offsides', 0)
    away_offsides = stats['away'].get('offsides', 0)
    
    # If values are 0, try API-specific keys
    if home_offsides == 0:
        home_offsides = stats['home'].get('Offsides', 0)
    if away_offsides == 0:
        away_offsides = stats['away'].get('Offsides', 0)
    
    total_offsides = home_offsides + away_offsides
    
    return {
        "overUnder": float(total_offsides),
        "teamTotals": {
            "home": float(home_offsides),
            "away": float(away_offsides)
        }
    }

def _settle_goal_timing_intervals(timeline: List[Dict[str, Any]]) -> List[str]:
    """Settle goal timing interval markets"""
    intervals = []
    
    for event in timeline:
        if event['type'] == 'goal':
            minute = event['minute']
            
            if 0 <= minute <= 15:
                intervals.append("0-15")
            elif 16 <= minute <= 30:
                intervals.append("16-30")
            elif 31 <= minute <= 45:
                intervals.append("31-45")
            elif minute == 45:
                intervals.append("45+")
            elif 46 <= minute <= 60:
                intervals.append("46-60")
            elif 61 <= minute <= 75:
                intervals.append("61-75")
            elif 76 <= minute <= 90:
                intervals.append("76-90")
            elif minute >= 90:
                intervals.append("90+")
    
    return list(set(intervals))  

if __name__ == "__main__":
    event_id = 2090582
    results = settle_soccer_game_props(event_id)
    print(json.dumps(results, indent=2))
