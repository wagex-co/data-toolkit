import asyncio
import json
import logging
import argparse
from src.blockchain.settlement_service import SettlementService
from src.config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    parser = argparse.ArgumentParser(description="Run the settlement process")
    parser.add_argument("--events-file", type=str, help="Path to events JSON file")
    parser.add_argument('--test-mode', action='store_true', help='Run in test mode without API calls')
    args = parser.parse_args()
    
    # load events from file if provided, otherwise use an empty dictionary
    if args.events_file:
        with open(args.events_file, 'r') as f:
            event_dictionary = json.load(f)
    else:
        event_dictionary = {}
        
    # create settlement service
    settlement_service = SettlementService(test_mode=args.test_mode)
    
    # run settlement cycle
    results = await settlement_service.run_settlement_cycle(event_dictionary)
    
    # print
    print(json.dumps(results, indent=2))
    
    # save results to file
    with open("settlement_results.json", "w") as f:
        json.dump(results, f, indent=2)
        
    logger.info("Settlement process completed")

if __name__ == "__main__":
    asyncio.run(main())
