from scrapegraphai.graphs import SmartScraperMultiGraph
import json
from src.config.settings import settings
from datetime import datetime
import os
from pathlib import Path

def scrape_over_unders(leagues_data: dict, sources: list = None) -> dict:
    """
    Scrape over/under totals for games across different leagues.
    
    Args:
        leagues_data (dict): Dictionary containing league and team information
        sources (list, optional): List of URLs to scrape. Defaults to ESPN URLs from settings.
        
    Returns:
        dict: Scraped over/under data organized by league
    """
    # Use default sources if none provided
    if sources is None:
        sources = list(settings.ESPN_URLS.values())

    # Configure the scraping pipeline
    graph_config = {
        "llm": {
            "api_key": settings.OPENAI_API_KEY,
            "model": settings.LLM_MODEL,
        },
        **settings.SCRAPER_CONFIG
    }

    # Create the SmartScraperMultiGraph instance
    smart_scraper_graph = SmartScraperMultiGraph(
        prompt=f'''Extract the over unders total for each game. 
        Ensure the team names are correct and complete, they should be the full team name, not the short name.
        The output should be segregated by league so each league should have a list of games with the over unders totals and the team names.
        Use the following names for the leagues: {list(leagues_data.keys())}
        ''',
        source=sources,
        config=graph_config
    )

    # Run the pipeline and get results
    result = smart_scraper_graph.run()
    
    return result

def main():
    # Get the project root directory (assuming src is in project root)
    # Create data directory if it doesn't exist
    os.makedirs("./data", exist_ok=True)
    
    # Generate timestamp for filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Load leagues data from the same directory as the script
    script_dir = Path(__file__).parent
    with open(script_dir / 'leagues_data.json', 'r') as f:
        leagues_data = json.load(f)
    
    # Scrape over/under data
    result = scrape_over_unders(leagues_data)
    
    # Save results with timestamp in data directory
    output_file = f'./data/over_unders_{timestamp}.json'
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=4)

if __name__ == "__main__":
    main() 