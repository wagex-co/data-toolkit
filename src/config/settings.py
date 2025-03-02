from pydantic_settings import BaseSettings
from typing import Dict
from pydantic import Field
import json

class Settings(BaseSettings):
    # API Keys
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    SPORTSDB_API_KEY: str = Field(..., env="SPORTSDB_API_KEY")
    
    # LLM Configuration
    LLM_MODEL: str = "openai/gpt-4o-mini"
    SCRAPER_CONFIG: Dict = {
        "verbose": True,
        "headless": True,
    }

    LEAGUE_DATA: Dict = json.load(open('DATA_MAIN/league_data.json'))
    
    # ESPN URLs Mapping
    ESPN_URLS: Dict[str, str] = {
        "NBA": "https://www.espn.com/nba/schedule",
        "NFL": "https://www.espn.com/nfl/schedule",
        "NHL": "https://www.espn.com/nhl/schedule",
        "Uefa Champions League": "https://www.espn.com/soccer/schedule/_/league/uefa.champions",
        "Uefa Europa League": "https://www.espn.com/soccer/schedule/_/league/uefa.europa",
        "English Premier League": "https://www.espn.com/soccer/schedule/_/league/eng.1",
        "Bundesliga": "https://www.espn.com/soccer/schedule/_/league/ger.1",
        "La Liga": "https://www.espn.com/soccer/schedule/_/league/esp.1",
        "Serie A": "https://www.espn.com/soccer/schedule/_/league/ita.1",
    }
    
    # League IDs for TheSportsDB
    LEAGUE_IDS: Dict[str, str] = {
        "English Premier League": "4328",
        "La Liga": "4335",
        "Bundesliga": "4331",
        "Serie A": "4332",
        "Uefa Champions League": "4480",
        "Uefa Europa League": "4481",
        "NFL": "4391",
        "NBA": "4387",
        "NHL": "4380",
        "MLB": "4424"
    }

    # ESPN League Name Mappings
    ESPN_LEAGUE_NAMES: Dict[str, str] = {
        "English Premier League": "Premier League",
        "La Liga": "La Liga",
        "Bundesliga": "Bundesliga",
        "Serie A": "Serie A",
        "Uefa Champions League": "Champions League",
        "Uefa Europa League": "Europa League",
        "NFL": "NFL",
        "NBA": "NBA",
        "MLB": "MLB",
        "NHL": "NHL"
    }

    class Config:
        env_file = ".env"
        case_sensitive = True

# Create a global settings instance
settings = Settings() 