import bittensor as bt
from typing import Optional

class PingSynapse(bt.Synapse):
    """
    Unified Synapse for Ping operations between Validator and Miner.
    """
    hotkey: str  # Validator sets this
    token: Optional[str] = None  # Miner sets this
