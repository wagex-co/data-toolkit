import json
import logging
from typing import Dict, Any, Optional
from web3 import Web3
# from web3.middleware.validation import geth_poa_middleware
from eth_account import Account
from eth_account.signers.local import LocalAccount
from src.config.settings import settings

logger = logging.getLogger(__name__)

class BlockchainClient:
    """Client for interacting with blockchain smart contracts."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Connect to the blockchain
        self.w3 = Web3(Web3.HTTPProvider(settings.RPC_URL))
        
        # Set up the account
        self.private_key = settings.PRIVATE_KEY
        self.account = self.w3.eth.account.from_key(self.private_key)
        self.account_address = self.account.address
        
        # Set the default account
        self.w3.eth.default_account = self.account_address
        
        # Load contract ABIs
        with open(settings.ORACLE_ABI_PATH, 'r') as f:
            oracle_artifact = json.load(f)
            self.oracle_abi = oracle_artifact['abi'] if 'abi' in oracle_artifact else oracle_artifact
        
        with open(settings.USDC_INTEGRATION_ABI_PATH, 'r') as f:
            usdc_integration_artifact = json.load(f)
            self.usdc_integration_abi = usdc_integration_artifact['abi'] if 'abi' in usdc_integration_artifact else usdc_integration_artifact
        
        # Initialize contracts
        self.oracle = self.w3.eth.contract(
            address=settings.ORACLE_ADDRESS,
            abi=self.oracle_abi
        )
        
        self.usdc_integration = self.w3.eth.contract(
            address=settings.USDC_INTEGRATION_ADDRESS,
            abi=self.usdc_integration_abi
        )
        
        self.logger.info(f"Initialized blockchain client with account: {self.account_address}")
        
    def submit_event_result(self, event_id, winner):
        try:
            # Convert event_id to int if it's a string
            event_id = int(event_id)
            
            # Get the nonce for the transaction
            nonce = self.w3.eth.get_transaction_count(self.account_address)
            
            # Build the transaction
            txn = self.oracle.functions.submitEventResult(
                event_id, 
                winner
            ).build_transaction({
                'from': self.account_address,
                'nonce': nonce,
                'gas': 2000000,
                # For Hardhat node, you can use simple gas price
                'gasPrice': self.w3.to_wei('1', 'gwei')
            })
            
            # Sign the transaction
            signed_txn = self.w3.eth.account.sign_transaction(txn, private_key=self.private_key)
            
            # Send the raw transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)  # Note: raw_transaction not rawTransaction
            
            # Wait for the transaction to be mined
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return {
                'status': 'success' if receipt.status == 1 else 'failed',
                'transaction_hash': self.w3.to_hex(receipt.transactionHash)
            }
        except Exception as e:
            self.logger.error(f"Error submitting event result: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }
            
    def resolve_bet(self, escrow_id):
        try:
            # Get the nonce for the transaction
            nonce = self.w3.eth.get_transaction_count(self.account_address)
            
            # Build the transaction
            txn = self.usdc_integration.functions.resolveBet(
                escrow_id
            ).build_transaction({
                'from': self.account_address,
                'nonce': nonce,
                'gas': 2000000,
                # For Hardhat node, you can use simple gas price
                'gasPrice': self.w3.to_wei('1', 'gwei')
            })
            
            # Sign the transaction
            signed_txn = self.w3.eth.account.sign_transaction(txn, private_key=self.private_key)
            
            # Send the raw transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)  # Note: raw_transaction not rawTransaction
            
            # Wait for the transaction to be mined
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return {
                'status': 'success' if receipt.status == 1 else 'failed',
                'transaction_hash': self.w3.to_hex(receipt.transactionHash)
            }
        except Exception as e:
            self.logger.error(f"Error resolving bet: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }
            
    def get_all_active_escrows(self) -> Dict[int, Dict[str, Any]]:
        """
        Get all active escrows from the USDCIntegration contract.
        
        Returns:
            Dictionary of escrow_id -> escrow_data
        """
        try:
            next_escrow_id = self.usdc_integration.functions.nextEscrowId().call()
            active_escrows = {}
            
            for escrow_id in range(next_escrow_id):
                escrow = self.usdc_integration.functions.getEscrow(escrow_id).call()
                if escrow[5]:  # escrow.exists
                    active_escrows[escrow_id] = {
                        'maker': escrow[0],
                        'taker': escrow[1],
                        'makerAmount': escrow[2],
                        'takerAmount': escrow[3],
                        'odds': escrow[4],
                        'exists': escrow[5],
                        'makerNFTTokenId': escrow[6],
                        'takerNFTTokenId': escrow[7],
                        'expirationTime': escrow[8],
                        'matchedAmount': escrow[9],
                        'withdrawn': escrow[10],
                        'eventId': escrow[11]
                    }
            
            return active_escrows
            
        except Exception as e:
            logger.error(f"Error getting active escrows: {e}")
            return {}
