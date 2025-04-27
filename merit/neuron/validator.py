import bittensor as bt
import pyotp
import asyncio
import os
import json
import hashlib
import base64
import ipaddress
from merit.protocol.merit_protocol import PingRequest, PingResponse
from merit.config import merit_config

class Validator:
    def __init__(self, config: bt.Config):
        bt.logging.info("Initializing Validator...")

        self.wallet = bt.wallet(config=config)
        self.subtensor = bt.subtensor(config=config)
        self.dendrite = bt.dendrite(wallet=self.wallet)

        self.netuid = config.netuid
        self.ping_frequency = config.ping_frequency

        os.makedirs(merit_config.EPOCH_RESULTS_DIR, exist_ok=True)

        self.latest_ping_success = {}
        self.ping_task = None

        # Fetch hyperparameters dynamically
        hyperparams = self.subtensor.get_subnet_hyperparameters(netuid=self.netuid)
        self.weights_version = int(hyperparams.weights_version)

        self.metagraph = self.subtensor.metagraph(netuid=self.netuid)

        self.state = self._load_state()
        self.health = self._load_health()

    def _load_state(self):
        if os.path.isfile(merit_config.STATE_FILE):
            with open(merit_config.STATE_FILE, "r") as f:
                return json.load(f)
        else:
            return {}

    def _save_state(self):
        with open(merit_config.STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=4)

    def _clear_state(self):
        if os.path.isfile(merit_config.STATE_FILE):
            os.remove(merit_config.STATE_FILE)

    def _load_health(self):
        if os.path.isfile(merit_config.HEALTH_FILE):
            with open(merit_config.HEALTH_FILE, "r") as f:
                return json.load(f)
        else:
            return {}

    def _save_health(self):
        with open(merit_config.HEALTH_FILE, "w") as f:
            json.dump(self.health, f, indent=4)

    def is_valid_public_ipv4(self, ip: str) -> bool:
        try:
            parsed_ip = ipaddress.IPv4Address(ip)
            return parsed_ip.is_global
        except ipaddress.AddressValueError:
            return False

    async def ping_miner(self, uid: int, hotkey: str) -> bool:
        axon = self.metagraph.axons[uid]

        if not self.is_valid_public_ipv4(axon.ip) or axon.port == 0:
            bt.logging.debug(f"Skipping ping for hotkey {hotkey}: Invalid or non-public IPv4 address {axon.ip}:{axon.port}")
            return False

        try:
            request = PingRequest(hotkey=hotkey)
            response = await self.dendrite.forward(
                axon,
                request,
                timeout=merit_config.PING_TIMEOUT,
            )

            if isinstance(response, PingResponse):
                hashed = hashlib.sha256(hotkey.encode('utf-8')).digest()
                base32_secret = base64.b32encode(hashed).decode('utf-8').strip('=')

                totp = pyotp.TOTP(base32_secret)
                if totp.verify(response.token, valid_window=1):
                    return True
        except Exception as e:
            bt.logging.warning(f"Ping failed for {hotkey}: {e}")

        return False

    async def _background_pinger(self):
        while True:
            try:
                self.metagraph = self.subtensor.metagraph(netuid=self.netuid)

                for uid in range(len(self.metagraph.hotkeys)):
                    if self.metagraph.validator_permit[uid]:
                        continue

                    hotkey = self.metagraph.hotkeys[uid]

                    axon = self.metagraph.axons[uid]
                    if not self.is_valid_public_ipv4(axon.ip) or axon.port == 0:
                        continue

                    success = await self.ping_miner(uid, hotkey)
                    self.latest_ping_success[hotkey] = success

                bt.logging.debug(f"Background pinger updated {len(self.latest_ping_success)} miners.")

            except Exception as e:
                bt.logging.error(f"Background pinging error: {e}")

            await asyncio.sleep(self.ping_frequency)

    async def run(self):
        bt.logging.info("Validator running...")

        if self.ping_frequency:
            self.ping_task = asyncio.create_task(self._background_pinger())

        try:
            while True:
                self.metagraph = self.subtensor.metagraph(netuid=self.netuid)

                # Refresh weights_version dynamically every epoch
                hyperparams = self.subtensor.get_subnet_hyperparameters(netuid=self.netuid)
                self.weights_version = int(hyperparams.weights_version)

                uids = []
                scores = []

                results = []

                for uid in range(len(self.metagraph.hotkeys)):
                    if self.metagraph.validator_permit[uid]:
                        bt.logging.debug(f"Skipping validator hotkey {self.metagraph.hotkeys[uid]}")
                        continue

                    hotkey = self.metagraph.hotkeys[uid]
                    coldkey = self.metagraph.coldkeys[uid]
                    incentive = float(self.metagraph.incentive[uid])

                    axon = self.metagraph.axons[uid]

                    bmps = incentive

                    if not self.is_valid_public_ipv4(axon.ip) or axon.port == 0:
                        bt.logging.debug(f"Invalid axon for hotkey {hotkey}, setting BMPS=0.0")
                        bmps = 0.0
                    else:
                        ping_success = self.latest_ping_success.get(hotkey, False) if self.ping_frequency else await self.ping_miner(uid, hotkey)

                        if bmps > 0.0:
                            if ping_success:
                                bmps += merit_config.PING_SUCCESS_BONUS
                            else:
                                bmps -= merit_config.PING_FAILURE_PENALTY
                        else:
                            bt.logging.debug(f"Hotkey {hotkey} has BMPS <= 0. Skipping ping reward adjustment.")

                    uids.append(uid)
                    scores.append(max(bmps, 0.0))

                    results.append({
                        "hotkey": hotkey,
                        "coldkey": coldkey,
                        "average_incentive": incentive,
                        "bmps_score": bmps,
                        "valid_ip": self.is_valid_public_ipv4(axon.ip) and axon.port != 0,
                    })

                    self.state[hotkey] = bmps
                    self._save_state()

                total_bmps = sum(scores)
                normalized_weights = [score / total_bmps if total_bmps > 0 else 0 for score in scores]

                if len(normalized_weights) > 0:
                    self.subtensor.set_weights(
                        wallet=self.wallet,
                        netuid=self.netuid,
                        uids=uids,
                        weights=normalized_weights,
                        version=self.weights_version,
                    )
                    bt.logging.success(f"Epoch {self.subtensor.get_current_block()}: Weights set successfully.")
                else:
                    bt.logging.warning("No valid miners found to set weights for.")

                block = self.subtensor.get_current_block()
                path = os.path.join(merit_config.EPOCH_RESULTS_DIR, f"epoch_{block}.json")
                with open(path, "w") as f:
                    json.dump(results, f, indent=4)

                self._clear_state()
                self._prune_epoch_results()

                await asyncio.sleep(merit_config.TEMPO)

        except asyncio.CancelledError:
            bt.logging.warning("Validator shutdown requested.")
        finally:
            if self.ping_task:
                self.ping_task.cancel()
                await self.ping_task

    def _prune_epoch_results(self):
        files = sorted(
            [f for f in os.listdir(merit_config.EPOCH_RESULTS_DIR) if f.startswith("epoch_") and f.endswith(".json")],
            key=lambda x: os.path.getmtime(os.path.join(merit_config.EPOCH_RESULTS_DIR, x))
        )

        if len(files) > merit_config.MAX_EPOCH_FILES:
            to_delete = files[:-merit_config.MAX_EPOCH_FILES]
            for f in to_delete:
                os.remove(os.path.join(merit_config.EPOCH_RESULTS_DIR, f))
                bt.logging.debug(f"Deleted old epoch file: {f}")
