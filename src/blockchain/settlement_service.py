import logging
import asyncio
from typing import Dict, Any, List, Tuple
from src.blockchain.client import BlockchainClient
from src.SportsDB.Event_Settlement.settle_events import settle_events
from src.config.settings import settings

logger = logging.getLogger(__name__)

class SettlementService:
    """Service for automating the settlement of bets based on sports results."""
    
    def __init__(self, test_mode=False):
        self.test_mode = test_mode
        self.blockchain_client = BlockchainClient()
        self.settle_events_client = settle_events
        
    async def map_event_to_blockchain(self, sports_event_id: str) -> int:
        """
        Map a sports event ID to a blockchain event ID.
        In our real implementation, we would have a database mapping between
        your sports event IDs and blockchain event IDs.
        """
        # Not prod ready, just a placeholder for now
        # Prod ready would be to look up the mapping in a database or other storage
        try:
            # Simple hash function for demo purposes
            return int(sports_event_id) % 1000000
        except ValueError:
            # If sports_event_id is not numeric, use a hash
            return hash(sports_event_id) % 1000000
            
    def map_outcome_to_winner(self, outcome: str) -> int:
        """Map a sports outcome to a winner value for the blockchain."""
        if outcome == "HOME":
            return 1  # Maker wins
        elif outcome == "AWAY":
            return 2  # Taker wins
        elif outcome == "DRAW":
            return 3  # Draw
        else:
            raise ValueError(f"Invalid outcome: {outcome}")
            
    async def process_event_settlements(self, event_dictionary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process event settlements and submit results to the blockchain.
        
        Args:
            event_dictionary: Dictionary of events to settle
            
        Returns:
            Dictionary with settlement results
        """
        # settle events - pass the test_mode flag
        settlement_results = await self.settle_events_client.settle_events(event_dictionary, test_mode=self.test_mode)
        
        # track results from blockchain
        blockchain_results = {}
        
        # process each settled event
        for event_id, event_data in settlement_results["events"].items():
            if isinstance(event_data, str):
                blockchain_results[event_id] = {"status": "error", "message": event_data}
                continue
                
            event_update = event_data.get("event_update")
            if not event_update:
                blockchain_results[event_id] = {"status": "error", "message": "No event update found"}
                continue
                
            # skip cancelled events
            if event_update.get("status") == "CANCELLED":
                blockchain_results[event_id] = {"status": "skipped", "message": "Event cancelled"}
                continue
                
            # get result
            result = event_update.get("result")
            if not result:
                blockchain_results[event_id] = {"status": "error", "message": "No result found"}
                continue
                
            # parse result (format: "home_score-away_score")
            try:
                home_score, away_score = map(int, result.split("-"))
                
                # determine winner
                if home_score > away_score:
                    winner = 1  # Home/Maker wins
                elif away_score > home_score:
                    winner = 2  # Away/Taker wins
                else:
                    winner = 3  # Draw
                    
                # map to blockchain event ID
                blockchain_event_id = await self.map_event_to_blockchain(event_id)
                
                # submit result to blockchain
                tx_hash = self.blockchain_client.submit_event_result(blockchain_event_id, winner)
                
                if tx_hash:
                    blockchain_results[event_id] = {
                        "status": "success", 
                        "blockchain_event_id": blockchain_event_id,
                        "winner": winner,
                        "tx_hash": tx_hash
                    }
                else:
                    blockchain_results[event_id] = {
                        "status": "already_submitted",
                        "blockchain_event_id": blockchain_event_id,
                        "winner": winner
                    }
                    
            except Exception as e:
                blockchain_results[event_id] = {"status": "error", "message": str(e)}
                
        return {
            "sports_settlement": settlement_results,
            "blockchain_settlement": blockchain_results
        }
        
    async def resolve_pending_bets(self) -> Dict[str, Any]:
        """
        Find and resolve all pending bets that have event results.
        
        Returns:
            Dictionary with resolution results
        """
        # get all active escrows
        active_escrows = self.blockchain_client.get_all_active_escrows()
        
        resolution_results = {}
        
        # try to resolve each escrow
        for escrow_id, escrow_data in active_escrows.items():
            event_id = escrow_data["eventId"]
            
            try:
                # try to resolve the bet
                tx_hash = self.blockchain_client.resolve_bet(escrow_id)
                
                if tx_hash:
                    resolution_results[escrow_id] = {
                        "status": "success",
                        "event_id": event_id,
                        "tx_hash": tx_hash
                    }
                else:
                    resolution_results[escrow_id] = {
                        "status": "failed",
                        "event_id": event_id,
                        "message": "Transaction failed or event not settled yet"
                    }
                    
            except Exception as e:
                resolution_results[escrow_id] = {
                    "status": "error",
                    "event_id": event_id,
                    "message": str(e)
                }
                
        return resolution_results
        
    async def run_settlement_cycle(self, event_dictionary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a complete settlement cycle:
        1. Process event settlements
        2. Resolve pending bets
        
        Args: event_dictionary: Dictionary of events to settle
            
        Returns: Dictionary with complete results
        """
        # process event settlements 
        settlement_results = await self.process_event_settlements(event_dictionary)
        
        # resolve pending bets
        resolution_results = await self.resolve_pending_bets()
        
        return {
            "settlement": settlement_results,
            "resolution": resolution_results
        }
