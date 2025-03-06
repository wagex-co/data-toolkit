from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
import pandas as pd
import json
from datetime import datetime
import os

from src.config.settings import settings
from src.WebScraping.utils.types import ProcessedDataResult
from src.WebScraping.utils.utils import map_team_name

def extract_over_under(odds_element):
    """Extract over/under value from odds element."""
    try:
        over_under_elements = odds_element.find_elements(By.CLASS_NAME, "db")
        for element in over_under_elements:
            text = element.text
            if text.startswith("O/U:"):
                return text.split(" ")[-1]
        return None
    except Exception:
        return None

def scrape_over_under(url: str):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--remote-debugging-port=9222")

    if settings.PYTHON_ENV == 'production':
        chrome_options.binary_location = "/usr/bin/chromium-browser"
        chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')
        service = Service(executable_path=chromedriver_path) 
        driver = webdriver.Chrome(options=chrome_options, service=service)
    else:
        driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(url)
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "Table__TBODY")))
        
        games_data = []
        
        schedule_tables = driver.find_elements(By.CLASS_NAME, "ScheduleTables")
        
        for schedule_table in schedule_tables:
            date_element = schedule_table.find_element(By.CLASS_NAME, "Table__Title")
            date = date_element.text
            
            game_rows = schedule_table.find_elements(By.CSS_SELECTOR, ".Table__TBODY tr")
            
            for row in game_rows:
                if "Table__TR--note" in row.get_attribute("class"):
                    continue
                
                try:
                    teams = row.find_elements(By.CLASS_NAME, "Table__Team")
                    if not teams:
                        continue
                        
                    away_team = teams[0].text.strip() if len(teams) > 0 else "N/A"
                    home_team = teams[1].text.strip() if len(teams) > 1 else "N/A"
                    
                    away_team = ' '.join(away_team.split())
                    home_team = ' '.join(home_team.split())
                    
                    time_elements = row.find_elements(By.CLASS_NAME, "Table__TD")
                    game_time = None
                    for elem in time_elements:
                        if any(x in elem.get_attribute("class").lower() for x in ["date__col", "time"]):
                            game_time = elem.text.strip()
                            break
                    if not game_time:
                        game_time = time_elements[0].text.strip() if time_elements else "N/A"
                    
                    over_under = None
                    try:
                        odds_elements = row.find_elements(By.CLASS_NAME, "Odds__Message")
                        if odds_elements:
                            over_under = extract_over_under(odds_elements[0])
                    except Exception as e:
                        print(f"Error extracting odds for {away_team} vs {home_team} on {date}: {e}")
                    
                    if over_under:  
                        games_data.append({
                            'Date': date,
                            'Away Team': away_team,
                            'Home Team': home_team,
                            'Time/Status': game_time,
                            'Over/Under': over_under
                        })
                except Exception as e:
                    print(f"Error processing row: {e}")
                    continue
        
        df = pd.DataFrame(games_data)
        return df
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
        
    finally:
        driver.quit()

def process_and_save_data(sources: dict = settings.ESPN_URLS, json_save: bool = False) -> ProcessedDataResult:
    """
    Process and save data in the same format as the original script.
    
    Args:
        sources (dict): Dictionary of league URLs to scrape (optional)
    
    Returns:
        dict: Processed data organized by league
    """
    result = {}
    
    for league, url in sources.items():
        df = scrape_over_under(url)
        if df is not None:
            games_list = []
            for _, row in df.iterrows():
                mapped_away_team = map_team_name(row['Away Team'], league)
                mapped_home_team = map_team_name(row['Home Team'], league)
                game_data = {
                    "date": row['Date'],
                    "teams": (mapped_away_team, mapped_home_team),
                    "time": row['Time/Status'],
                    "over_under": row['Over/Under']
                }
                games_list.append(game_data)
            
            result[league] = games_list
        else:
            print(f"No data found for {league}")
    
    if json_save:
        # Create data directory if it doesn't exist
        os.makedirs("./src/WebScraping/data", exist_ok=True)
        # Save results with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'./src/WebScraping/data/over_unders_{timestamp}.json'
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=4)
    return result

if __name__ == "__main__":
    result = process_and_save_data(sources=settings.ESPN_URLS, json_save=True)
