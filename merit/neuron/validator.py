import bittensor as bt
import pyotp
import asyncio
import os
import json
import hashlib
import base64
import ipaddress
import time
from merit.protocol.merit_protocol import PingSynapse
from merit.config import merit_config

class Validator:
    def __init__(self, config: bt.Config):
        bt.logging.info("Initializing Validator...")

        self.wallet = bt.wallet(config=config)
        self.subtensor = bt.subtensor(config=config)
        self.dendrite = bt.dendrite(wallet=self.wallet)
        self.netuid = config.netuid
        self.ping_frequency = config.ping_frequency or 600
        self.eval_frequency = config.eval_frequency or 600
        self.last_eval_time = 0
        self.no_zero_weights = config.no_zero_weights or False
        os.makedirs(merit_config.EPOCH_RESULTS_DIR, exist_ok=True)
        self.latest_ping_success = {}
        self.ping_task = None
        self.first_ping_done = False
        self.metagraph = self.subtensor.metagraph(netuid=self.netuid)
        self.state = self._load_state()
        self.health = self._load_health()
        self.all_metagraphs_info = self._fetch_all_metagraphs_info()

    def _fetch_all_metagraphs_info(self):
        try:
            infos = self.subtensor.get_all_metagraphs_info()
            bt.logging.success(f"Fetched {len(infos)} metagraphs info.")
            return infos
        except Exception as e:
            bt.logging.warning(f"Failed to fetch all metagraphs info: {e}")
            return []

    def _load_state(self):
        if os.path.isfile(merit_config.STATE_FILE):
            with open(merit_config.STATE_FILE, "r") as f:
                return json.load(f)
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
        return {}

    def _save_health(self):
        with open(merit_config.HEALTH_FILE, "w") as f:
            json.dump(self.health, f, indent=4)

    def _prune_epoch_results(self, keep_last=5):
        files = sorted([
            f for f in os.listdir(merit_config.EPOCH_RESULTS_DIR) if f.startswith("epoch_")
        ])
        for old_file in files[:-keep_last]:
            os.remove(os.path.join(merit_config.EPOCH_RESULTS_DIR, old_file))

    def is_valid_public_ipv4(self, ip: str) -> bool:
        try:
            parsed_ip = ipaddress.IPv4Address(ip)
            return parsed_ip.is_global
        except ipaddress.AddressValueError:
            return False

    async def _is_port_open(self, ip: str, port: int) -> bool:
        try:
            await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=4.0)
            return True
        except Exception:
            return False

    async def ping_miner(self, neuron) -> bool:
        axon = neuron.axon_info
        ip = axon.ip
        port = axon.port

        if not self.is_valid_public_ipv4(ip) or port == 0:
            bt.logging.debug(f"Skipping invalid IP/port for {neuron.hotkey}: {ip}:{port}")
            return False

        if not await self._is_port_open(ip, port):
            bt.logging.debug(f"Port closed for {neuron.hotkey}: {ip}:{port}")
            return False

        try:
            request = PingSynapse(hotkey=neuron.hotkey)
            response = await self.dendrite.forward(axon, request, timeout=merit_config.PING_TIMEOUT)

            if not isinstance(response, PingSynapse) or not response.token:
                bt.logging.debug(f"Invalid response or missing token from {neuron.hotkey}")
                return False

            hashed = hashlib.sha256(neuron.hotkey.encode('utf-8')).digest()
            base32_secret = base64.b32encode(hashed).decode('utf-8').strip('=')
            totp = pyotp.TOTP(base32_secret)

            if not totp.verify(response.token, valid_window=1):
                bt.logging.debug(f"TOTP failed for {neuron.hotkey}")
                return False

            bt.logging.debug(f"Ping success for {neuron.hotkey}")
            return True

        except Exception as e:
            bt.logging.debug(f"Ping exception for {neuron.hotkey}: {e}")
            return False

    async def _background_pinger(self):
        while True:
            try:
                self.metagraph.sync(subtensor=self.subtensor)
                self.all_metagraphs_info = self._fetch_all_metagraphs_info()
                bt.logging.debug("Starting background ping round...")

                tasks = []
                for neuron in self.metagraph.neurons:
                    if self._should_skip_neuron(neuron):
                        continue
                    tasks.append(self.ping_miner(neuron))

                results = await asyncio.gather(*tasks, return_exceptions=True)

                for neuron, success in zip(self.metagraph.neurons, results):
                    if self._should_skip_neuron(neuron):
                        continue
                    self.latest_ping_success[neuron.hotkey] = bool(success)

                reachable_count = sum(self.latest_ping_success.values())
                bt.logging.success(f"Ping round complete. {reachable_count} miners reachable.")
                self.first_ping_done = True

            except Exception as e:
                bt.logging.error(f"Background pinger error: {e}")

            await asyncio.sleep(self.ping_frequency)

    def _should_skip_neuron(self, neuron) -> bool:
        try:
            return neuron.dividends > 0 or neuron.validator_trust > 0
        except Exception:
            return False

    def _evaluate_miners(self):
        bt.logging.debug("Evaluating miners...")
        self.state = {}
        evaluated_count = 0

        for neuron in self.metagraph.neurons:
            if self._should_skip_neuron(neuron):
                continue
            if not self.latest_ping_success.get(neuron.hotkey, False):
                continue

            hotkey = neuron.hotkey
            incentives = []
            for info in self.all_metagraphs_info:
                if info.netuid in (0, self.netuid):
                    continue
                if hotkey in info.hotkeys:
                    idx = info.hotkeys.index(hotkey)
                    incentives.append(info.incentives[idx])

            if not incentives:
                continue

            avg_incentive = sum(incentives) / len(incentives)
            bmps = avg_incentive * 1000

            bt.logging.debug(f"Miner {hotkey}: Incentives={incentives}, Avg={avg_incentive:.6f}, BMPs={bmps:.2f}")
            self.state[hotkey] = bmps
            evaluated_count += 1

        self._save_state()
        bt.logging.info(f"Evaluated {evaluated_count} miners.")

    async def run(self):
        bt.logging.info("Validator running...")

        if self.ping_task is None:
            self.ping_task = asyncio.create_task(self._background_pinger())

        try:
            while True:
                current_block = self.subtensor.get_current_block()
                my_uid = self.metagraph.hotkeys.index(self.wallet.hotkey.ss58_address)
                blocks_since_update = self.subtensor.blocks_since_last_update(netuid=self.netuid, uid=my_uid)

                bt.logging.debug(
                    f"My UID: {my_uid}, blocks since last weights set: {blocks_since_update}, TEMPO: {merit_config.TEMPO}")

                if not self.first_ping_done:
                    bt.logging.debug("Waiting for first ping round to complete...")
                    await asyncio.sleep(3)
                    continue

                now = time.time()
                if now - self.last_eval_time >= self.eval_frequency:
                    self._evaluate_miners()
                    self.last_eval_time = now

                if blocks_since_update >= (merit_config.TEMPO - 2):
                    bt.logging.info("Enough blocks passed. Setting weights now...")

                    uids, scores = [], []
                    for neuron in self.metagraph.neurons:
                        if neuron.hotkey in self.state:
                            uids.append(neuron.uid)
                            scores.append(self.state[neuron.hotkey])

                    total_bmps = sum(scores)
                    if total_bmps == 0 and self.no_zero_weights and len(scores) > 0:
                        bt.logging.warning("All scores are zero, but --no_zero_weights is set. Assigning even weights.")
                        normalized_weights = [1.0 / len(scores)] * len(scores)
                    elif total_bmps > 0:
                        normalized_weights = [s / total_bmps for s in scores]
                    else:
                        normalized_weights = []

                    if normalized_weights:
                        bt.logging.info(f"Setting weights: total_bmps = {total_bmps:.4f}")
                        self.subtensor.set_weights(
                            wallet=self.wallet,
                            netuid=self.netuid,
                            uids=uids,
                            weights=normalized_weights,
                            version_key=self.metagraph.hparams.weights_version,
                            wait_for_inclusion=True,
                        )
                        bt.logging.success(f"Weights set successfully at block {current_block}.")
                    else:
                        bt.logging.warning("All scores are zero, skipping setting weights.")

                    # Save to disk
                    block = self.subtensor.get_current_block()
                    path = os.path.join(merit_config.EPOCH_RESULTS_DIR, f"epoch_{block}.json")
                    with open(path, "w") as f:
                        json.dump(self.state, f, indent=4)

                    self._clear_state()
                    self.state = {}  # Clear in-memory state
                    self._prune_epoch_results()
                else:
                    bt.logging.debug(f"Not enough blocks passed yet ({blocks_since_update}). Waiting...")

                await asyncio.sleep(12)

        except asyncio.CancelledError:
            bt.logging.warning("Validator shutdown requested.")
        finally:
            if self.ping_task:
                self.ping_task.cancel()
                await self.ping_task
