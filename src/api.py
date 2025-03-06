from flask import Flask, request, jsonify
import asyncio
from datetime import datetime
from src.WebScraping.scraper_ou import process_and_save_data
from src.SportsDB.Event_Creation.create_events import create_events
from src.SportsDB.Event_Settlement.settle_events import settle_events
from src.config.settings import settings
from functools import wraps

app = Flask(__name__)

def require_cron_secret(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        cron_secret = request.headers.get('x-cron-schedule-secret')
        if not cron_secret or cron_secret != settings.CRON_SECRET:
            return jsonify({"error": "Unauthorized - Invalid or missing cron secret"}), 401
        return f(*args, **kwargs)
    return decorated_function

# Helper function to run async functions
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/get-ou-lines', methods=['POST'])
@require_cron_secret
def api_get_ou_lines():
    """
    Endpoint to scrape over/under totals for games
    
    Request body should contain:
    - leagues_data (dict): Dictionary containing league and team information
    - sources (list, optional): List of URLs to scrape
    """
    try:
        data = request.json

        leagues = data.get('leagues', {})
        sources = {}
        for league in leagues:
            if league not in settings.ESPN_URLS:
                return jsonify({
                    "status": "error",
                    "message": f"Invalid league: {league}"
                }), 400
            sources[league] = settings.ESPN_URLS[league]

        result = process_and_save_data(sources=sources, json_save=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        return jsonify({
            "status": "success",
            "timestamp": timestamp,
            "data": result
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/create-events', methods=['POST'])
@require_cron_secret
def api_create_events():
    """
    Endpoint to create events from SportsDB
    
    Request body should contain:
    - leagues (dict): Dictionary mapping league names to SportsDB league IDs
    - days_to_fetch (int, optional): Number of days to fetch, default is 7
    - start_date (str, optional): Start date in YYYY-MM-DD format
    """
    try:
        data = request.json
        print(data)
        leagues = data.get('leagues', {})
        days_to_fetch = data.get('daysToFetch', 7)
        start_date = data.get('startDate', None)

        print(leagues)
        print("days_to_fetch", days_to_fetch)
        print("start_date", start_date)
        
        events_data, markets_data = run_async(
            create_events.create_events(leagues, days_to_fetch, start_date)
        )
        
        return jsonify({
            "status": "success",
            "events": events_data,
            "markets": markets_data
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/settle-events', methods=['POST'])
@require_cron_secret
def api_settle_events():
    """
    Endpoint to settle events based on event results
    
    Request body should contain:
    - unsettled_events (dict): Dictionary of unsettled events
    """
    try:
        data = request.json
        print(data)

        result = run_async(
            settle_events.settle_events(data)
        )
        
        return jsonify({
            "status": "success",
            "result": result
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=3002, debug=True) 