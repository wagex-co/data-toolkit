from flask import Flask
from src.routes.sportsdb import sportsdb_bp
from src.routes.api import api_bp
import asyncio

def create_app():
    """
    Application factory function to create and configure the Flask app
    
    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    
    # Helper function to run async functions
    def run_async(coro):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    # Make run_async available to the app context
    app.run_async = run_async
    
    # Register blueprints
    app.register_blueprint(sportsdb_bp)
    app.register_blueprint(api_bp)
    
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host='0.0.0.0', port=3002, debug=True) 