from flask import Flask, request, jsonify
import asyncio
from datetime import datetime
from src.WebScraping.scraper_ou import process_and_save_data
from src.SportsDB.Event_Creation.create_events import create_events
from src.SportsDB.Event_Settlement.settle_events import settle_events
from src.config.settings import settings

app = Flask(__name__)

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

@app.route('/scrape-over-unders', methods=['POST'])
def api_scrape_over_unders():
    """
    Endpoint to scrape over/under totals for games
    
    Request body should contain:
    - leagues_data (dict): Dictionary containing league and team information
    - sources (list, optional): List of URLs to scrape
    """
    try:
        data = request.json

        leagues = data.get('leagues', {})
        sources = {league: settings.ESPN_URLS[league] for league in leagues} if leagues else settings.ESPN_URLS

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
        leagues = data.get('leagues', {})
        days_to_fetch = data.get('days_to_fetch', 7)
        start_date = data.get('start_date', None)
        
        # Call the create_events function asynchronously
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

@app.route('/settle-markets', methods=['POST'])
def api_settle_markets():
    """
    Endpoint to settle markets based on event results
    
    Request body should contain:
    - unsettled_events (list): List of unsettled events
    - markets (list): List of markets to settle
    """
    try:
        data = request.json
        unsettled_events = data.get('unsettled_events', [])
        markets = data.get('markets', [])
        
        # Call the settle_markets function asynchronously
        result = run_async(
            settle_events.settle_markets(unsettled_events, markets)
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