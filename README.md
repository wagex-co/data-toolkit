# Sports Data Collection Toolkit

A professional toolkit for collecting and analyzing sports data from various sources, including league information, team details, and betting odds.

## Features

- League and team data collection from TheSportsDB
- Over/Under odds scraping from ESPN
- Support for multiple sports leagues:
  - NBA
  - NFL
  - NHL
  - UEFA Champions League
  - UEFA Europa League
  - English Premier League
  - Bundesliga
  - La Liga
  - Serie A

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/sports-data-toolkit.git
cd sports-data-toolkit

# Create and activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package in development mode
pip install -e ".[dev]"
```

## Configuration

The toolkit requires the following environment variables:

```bash
SPORTSDB_API_KEY=your_sportsdb_api_key
OPENAI_API_KEY=your_openai_api_key  # Required for odds scraping
```

Create a `.env` file in the project root and add these variables.

## Usage

### Collecting League and Team Data

```python
from sports_data.scrapers.league_details import get_league_data

# Fetch data for all supported leagues
league_data = get_league_data()
```

### Scraping Over/Under Odds

```python
from sports_data.scrapers.odds import get_over_under_odds

# Fetch current over/under odds
odds_data = get_over_under_odds()
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

The project uses Black for code formatting and isort for import sorting:

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/
```

### Type Checking

```bash
mypy src/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
