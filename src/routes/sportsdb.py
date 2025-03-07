from flask import Blueprint, jsonify, request
from src.WebScraping.utils.sportsdb_utilities import SportsDBAPI
from src.config.settings import settings
from functools import wraps

sportsdb_bp = Blueprint('sportsdb', __name__, url_prefix='/sportsdb')

# Authentication middleware
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('x-api-key')
        if settings.PYTHON_ENV == 'development':
            return f(*args, **kwargs)
        if not api_key or api_key != settings.API_KEY:
            return jsonify({"error": "Unauthorized - Invalid or missing API key"}), 401
        return f(*args, **kwargs)
    return decorated_function

@sportsdb_bp.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint for SportsDB API routes"""
    return jsonify({"status": "healthy", "service": "sportsdb"})

@sportsdb_bp.route('/players/team/<team_id>', methods=['GET'])
@require_api_key
def list_players_by_team_id(team_id):
    """
    Get all players for a team by team ID
    
    Args:
        team_id (str): The team ID to lookup
        
    Returns:
        JSON response with player data
    """
    try:
        api = SportsDBAPI()
        result = api.list_players_by_team_id(team_id)
        return jsonify({
            "status": "success",
            "data": result
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@sportsdb_bp.route('/schedule/league/season', methods=['GET'])
@require_api_key
def schedule_league_season():
    """
    Get full season schedule for a league
    
    Query parameters:
        league_id (str): ID of the league
        season (str): Season (e.g., "2023-2024")
        
    Returns:
        JSON response with league season schedule
    """
    try:
        league_id = request.args.get('league_id')
        season = request.args.get('season')
        
        if not league_id:
            return jsonify({
                "status": "error",
                "message": "Missing required parameter: league_id"
            }), 400
            
        if not season:
            return jsonify({
                "status": "error",
                "message": "Missing required parameter: season"
            }), 400
            
        api = SportsDBAPI()
        result = api.schedule_league_season(league_id, season)
        return jsonify({
            "status": "success",
            "data": result
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500 