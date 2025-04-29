import bittensor as bt
import pyotp
import asyncio
import os
import json
import hashlib
import base64
import ipaddress
from merit.protocol.merit_protocol import PingSynapse
from merit.config import merit_config

class Validator:
    def __init__(self, config: bt.Config):
        bt.logging.info("Initializing Validator...")

        self.wallet = bt.wallet(config=config)
        self.subtensor = bt.subtensor(config=config)
        self.dendrite = bt.dendrite(wallet=self.wallet)
        self.netuid = config.netuid
        self.ping_frequency = config.ping_frequency or 600  # every 10 minutes
        self.no_zero_weights = config.no_zero_weights or False # default False
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

            if not isinstance(response, PingSynapse):
                bt.logging.error(f"Invalid response type: {type(response)}")
                return False

            if not response.token:
                bt.logging.debug(f"Missing token from {neuron.hotkey}")
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

                bt.logging.success(f"Ping round complete. {sum(self.latest_ping_success.values())} miners reachable.")
                self.first_ping_done = True

            except Exception as e:
                bt.logging.error(f"Background pinger error: {e}")

            await asyncio.sleep(self.ping_frequency)

    def _should_skip_neuron(self, neuron) -> bool:
        try:
            if neuron.dividends > 0 or neuron.validator_trust > 0:
                bt.logging.debug(
                    f"Evaluating neuron {neuron.hotkey}: dividends={neuron.dividends}, trust={neuron.validator_trust}")
                return True
        except Exception:
            pass
        return False

    def compute_incentive_for_hotkey(self, hotkey: str) -> float:
        incentives = []
        active_subnet_count = len([info for info in self.all_metagraphs_info if info.netuid not in (0, self.netuid)])

        for info in self.all_metagraphs_info:
            if info.netuid in (0, self.netuid):
                continue
            if hotkey in info.hotkeys:
                idx = info.hotkeys.index(hotkey)
                incentives.append(info.incentives[idx])

        if active_subnet_count == 0:
            return 0.0

        total_incentive = sum(incentives)
        bt.logging.debug(f"Incentives for {hotkey}: {incentives}")
        return total_incentive / active_subnet_count

    async def run(self):
        bt.logging.info("Validator running...")

        # Start background pinger if not already started
        if self.ping_task is None:
            self.ping_task = asyncio.create_task(self._background_pinger())

        try:
            while True:
                current_block = self.subtensor.get_current_block()
                my_uid = self.metagraph.hotkeys.index(self.wallet.hotkey.ss58_address)
                blocks_since_update = self.subtensor.blocks_since_last_update(netuid=self.netuid, uid=my_uid)

                # Wait for first ping round to complete
                if not self.first_ping_done:
                    bt.logging.warning("Waiting for pinger to complete first round...")
                    await asyncio.sleep(3)
                    continue

                # Sync metagraph and fetch latest incentives only when close to setting weights
                if blocks_since_update >= (merit_config.TEMPO - 5):
                    bt.logging.debug(f"Preparing to set weights, syncing metagraph...")
                    self.metagraph.sync(subtensor=self.subtensor)
                    self.all_metagraphs_info = self._fetch_all_metagraphs_info()

                # If enough blocks passed, attempt to set weights
                if blocks_since_update >= (merit_config.TEMPO - 2):
                    bt.logging.info(f"Enough blocks passed ({blocks_since_update}). Setting weights...")

                    uids = []
                    scores = []

                    for neuron in self.metagraph.neurons:
                        hotkey = neuron.hotkey
                        coldkey = neuron.coldkey

                        # Log whether this neuron is being skipped
                        if self._should_skip_neuron(neuron):
                            bt.logging.debug(f"Skipping neuron {hotkey} due to dividend/trust exclusion.")
                            continue

                        # Fetch incentive
                        incentives = []
                        for info in self.all_metagraphs_info:
                            if info.netuid in (0, self.netuid):
                                continue
                            if hotkey in info.hotkeys:
                                idx = info.hotkeys.index(hotkey)
                                incentives.append(info.incentives[idx])

                        if len(incentives) == 0:
                            bt.logging.debug(f"No external incentives found for {hotkey}")

                        total_incentive = sum(incentives)
                        incentive = total_incentive / len(incentives) if incentives else 0.0
                        bmps = incentive * 1000.0

                        # Check axon validity
                        valid_axon = (
                                self.is_valid_public_ipv4(neuron.axon_info.ip)
                                and neuron.axon_info.port != 0
                                and self.latest_ping_success.get(hotkey, False)
                        )

                        bt.logging.debug(
                            f"{hotkey} | IP: {neuron.axon_info.ip}, Port: {neuron.axon_info.port}, "
                            f"Valid IP: {self.is_valid_public_ipv4(neuron.axon_info.ip)}, "
                            f"Ping: {self.latest_ping_success.get(hotkey, False)}, "
                            f"Axon Valid: {valid_axon}, Incentive: {incentive:.4f}, BMPs: {bmps:.2f}"
                        )

                        if not valid_axon:
                            bt.logging.warning(f"{hotkey} excluded due to invalid axon (ip/port/ping).")
                            bmps = 0.0

                        uids.append(neuron.uid)
                        scores.append(max(bmps, 0.0))
                        self.state[hotkey] = bmps

                    self._save_state()

                    total_bmps = sum(scores)

                    # Normalization
                    normalized_weights = [score / total_bmps if total_bmps > 0 else 0 for score in scores]

                    # Handle zero weights if --no_zero_weights was passed
                    if total_bmps == 0 and self.no_zero_weights:
                        bt.logging.warning("All scores are zero, but --no_zero_weights is set. Assigning even weights.")
                        normalized_weights = [1.0 / len(scores) for _ in scores]

                    if len(normalized_weights) > 0 and sum(normalized_weights) > 0:
                        bt.logging.info(f"Setting weights: total_bmps = {total_bmps:.4f}")

                        self.subtensor.set_weights(
                            wallet=self.wallet,
                            netuid=self.netuid,
                            uids=uids,
                            weights=normalized_weights,
                            version_key=self.metagraph.hparams.weights_version,
                            wait_for_inclusion=True,
                        )
                        bt.logging.success(f"Epoch {current_block}: Weights set successfully.")
                    else:
                        bt.logging.warning("All scores are zero, skipping setting weights.")

                    # Save results for audit
                    block = self.subtensor.get_current_block()
                    path = os.path.join(merit_config.EPOCH_RESULTS_DIR, f"epoch_{block}.json")
                    with open(path, "w") as f:
                        json.dump(self.state, f, indent=4)

                    # Clean old state and old epochs
                    self._clear_state()
                    self._prune_epoch_results()

                else:
                    # Sleep until next check
                    await asyncio.sleep(12)

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

