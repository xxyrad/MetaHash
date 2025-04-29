import bittensor as bt
import pyotp
import asyncio
import hashlib
import base64

from merit.protocol.merit_protocol import PingRequest, PingResponse
from merit.config import merit_config

class Miner:
    def __init__(self, config: bt.Config):
        bt.logging.info("Initializing Miner...")

        self.wallet = bt.wallet(config=config)
        self.subtensor = bt.subtensor(config=config)
        self.netuid = config.netuid

        self.axon = bt.axon(wallet=self.wallet, config=config)

        # Hotkey registration check
        self.metagraph = self.subtensor.metagraph(netuid=self.netuid)
        if self.wallet.hotkey.ss58_address not in self.metagraph.hotkeys:
            bt.logging.error(f"Hotkey {self.wallet.hotkey.ss58_address} is not registered on subnet {self.netuid}. Exiting.")
            exit(1)

        # Attach forward function
        self.axon.attach(self.handle_ping_request)

        # Start local axon server
        self.axon.start()
        bt.logging.success(f"Miner Axon started at {self.axon.external_ip}:{self.axon.external_port}")

        self.subtensor.serve_axon(
            axon=self.axon,
            netuid=self.netuid,
        )
        bt.logging.success(f"Miner served on netuid {self.netuid}.")

    async def handle_ping_request(self, synapse: PingRequest) -> PingResponse:
        """
        Handles incoming PingRequest and returns TOTP token and hotkey.
        """
        hotkey = self.wallet.hotkey.ss58_address

        # Generate TOTP token based on hotkey
        hashed = hashlib.sha256(hotkey.encode('utf-8')).digest()
        base32_secret = base64.b32encode(hashed).decode('utf-8').strip('=')
        totp = pyotp.TOTP(base32_secret)
        token = totp.now()

        bt.logging.debug(f"Responding with hotkey={hotkey} and token={token}")
        return PingResponse(hotkey=hotkey, token=token)

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
            bt.logging.warning("Miner shutdown complete.")
