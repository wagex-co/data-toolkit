# All Things Data Sourcing API

This repository contains a Flask API for sports data functions, including:
- Scraping over/under totals for games
- Creating sports events from SportsDB
- Settling markets based on event outcomes

## Setup

There are two ways to set up this project:

### 1. Development Installation

For development, you can install the package in editable mode:

```bash
# Clone the repository
git clone <repository-url>
cd AllThingsDataSourcing

# Install in development mode
pip install -e .
```

This allows you to modify the code and have the changes take effect immediately.

### 2. Regular Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

Make sure your `.env` file contains all required API keys:
```
OPENAI_API_KEY=your_openai_api_key
SPORTSDB_API_KEY=your_sportsdb_api_key
```

## Running the API

Start the Flask development server:
```
python src/api.py
```

For production use, it's recommended to use Gunicorn:
```
gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:5000 src.api:app
```

## API Endpoints

### Health Check
```
GET /health
```

### Scrape Over/Under Totals
```
POST /scrape-over-unders
```
Request body:
```json
{
  "leagues_data": {
    "NBA": { "teams": [...] },
    "NFL": { "teams": [...] }
  },
  "sources": ["https://example.com/nba", "https://example.com/nfl"]
}
```

### Create Events
```
POST /create-events
```
Request body:
```json
{
  "leagues": {
    "NBA": "4387",
    "NFL": "4391"
  },
  "days_to_fetch": 7,
  "start_date": "2023-03-01"
}
```

### Settle Markets
```
POST /settle-markets
```
Request body:
```json
{
  "unsettled_events": [
    {
      "_id": "event_id_1",
      "sportsdb_id": "sportsdb_event_id_1",
      "participants": ["Team A", "Team B"]
    }
  ],
  "markets": [
    {
      "_id": "market_id_1",
      "event_id": "event_id_1",
      "type": "moneyline"
    }
  ]
}
```

