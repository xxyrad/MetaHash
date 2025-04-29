# merit/protocol/merit_protocol.py

import bittensor as bt

class PingRequest(bt.Synapse):
    """
    Synapse for a validator to send a ping to a miner.
    """
    hotkey: str

class PingResponse(bt.Synapse):
    """
    Synapse for a miner to respond with a TOTP token.
    """
    hotkey: str
    token: str
