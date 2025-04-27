import bittensor as bt
import pyotp
import asyncio
import os
import json
import hashlib
import base64
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

    async def ping_miner(self, uid: int, hotkey: str) -> bool:
        axon = self.metagraph.axons[uid]
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
                    hotkey = self.metagraph.hotkeys[uid]
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

                results = []
                bmps_scores = []

                for uid in range(len(self.metagraph.hotkeys)):
                    hotkey = self.metagraph.hotkeys[uid]
                    coldkey = self.metagraph.coldkeys[uid]
                    incentive = float(self.metagraph.incentive[uid])

                    if self.ping_frequency:
                        ping_success = self.latest_ping_success.get(hotkey, False)
                    else:
                        ping_success = await self.ping_miner(uid, hotkey)

                    bmps = incentive
                    if ping_success:
                        bmps += merit_config.PING_SUCCESS_BONUS
                    else:
                        bmps -= merit_config.PING_FAILURE_PENALTY

                    results.append({
                        "hotkey": hotkey,
                        "coldkey": coldkey,
                        "average_incentive": incentive,
                        "ping_success": ping_success,
                        "bmps_score": bmps,
                    })

                    self.state[hotkey] = bmps
                    bmps_scores.append(max(bmps, 0.0))

                    prev_health = self.health.get(hotkey, merit_config.HEALTH_INITIAL)
                    if ping_success:
                        new_health = min(prev_health + merit_config.HEALTH_INCREASE, merit_config.HEALTH_MAX)
                    else:
                        new_health = max(prev_health - merit_config.HEALTH_DECREASE, 0)
                    self.health[hotkey] = new_health

                    self._save_state()
                    self._save_health()

                total_bmps = sum(bmps_scores)
                normalized_weights = [score / total_bmps if total_bmps > 0 else 0 for score in bmps_scores]

                self.subtensor.set_weights(
                    wallet=self.wallet,
                    netuid=self.netuid,
                    uids=list(range(len(self.metagraph.hotkeys))),
                    weights=normalized_weights,
                )

                block = self.subtensor.get_current_block()
                path = os.path.join(merit_config.EPOCH_RESULTS_DIR, f"epoch_{block}.json")
                with open(path, "w") as f:
                    json.dump(results, f, indent=4)

                bt.logging.success(f"Epoch {block}: Weights set and results saved.")

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
