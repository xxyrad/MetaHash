import bittensor as bt
import pyotp
import asyncio
import hashlib
import base64
from merit.protocol.merit_protocol import PingRequest, PingResponse
from merit.config import merit_config

class Miner:
    def __init__(self):
        bt.logging.info("Initializing Miner...")

        self.wallet = bt.wallet()
        self.subtensor = bt.subtensor(network=merit_config.NETWORK)

        # Set up Axon
        self.axon = bt.axon(wallet=self.wallet)
        self.axon.attach(self.handle_ping_request)  # <-- Corrected: no synapse_type param

        self.axon.start()
        bt.logging.success(f"Miner Axon started at {self.axon.external_ip}:{self.axon.external_port}")

    async def handle_ping_request(self, synapse: PingRequest) -> PingResponse:
        """
        Handles incoming PingRequest and returns TOTP token.
        """
        hotkey = self.wallet.hotkey.ss58_address

        # Hash the hotkey into a stable TOTP secret
        hashed = hashlib.sha256(hotkey.encode('utf-8')).digest()
        base32_secret = base64.b32encode(hashed).decode('utf-8').strip('=')

        totp = pyotp.TOTP(base32_secret)
        token = totp.now()

        bt.logging.debug(f"Responding with TOTP token {token}")
        return PingResponse(token=token)

    def run(self):
        """
        Runs the miner indefinitely.
        """
        bt.logging.info("Miner running...")
        try:
            loop = asyncio.get_event_loop()
            loop.run_forever()
        except KeyboardInterrupt:
            bt.logging.warning("Miner shutting down...")
            self.axon.stop()
