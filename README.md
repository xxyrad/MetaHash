# Merit Subnet

---

## Overview

**Merit** is a Bittensor Subnet (NetUID 73) designed to incentivize and reward miner participation across the broader Bittensor network.  
Validators on Merit measure miners' contributions to other subnets and reward based on verified uptime, cross-subnet incentive, and activity.

Merit establishes a **trust and reputation layer** that complements the Bittensor ecosystem, driving fairness, growth, and decentralization.

---

## Features

- 🔹 Dynamic cross-subnet miner scoring (BMPS - Bittensor Miner Participation Score)
- 🔹 Strict miner validation (TOTP verification, TCP preflight)
- 🔹 Robust handling of invalid or unreachable miners
- 🔹 Incentive ×1000 scaling for fair scoring
- 🔹 Uptime bonuses (+1.0 success / -0.25 penalty failure)
- 🔹 Fully dynamic weights_version fetching
- 🔹 Automatic pruning of old epochs (48 file retention)

---

## Quickstart

### 1. Clone the repository

```bash
git clone https://github.com/fx-integral/merit.git
cd merit
```

### 2. Set up a Python environment

```bash
python -m venv venv
source venv/bin/activate
pip install uv
uv pip install -r requirements.txt
```

---

## Running a Miner

```bash
python -m merit.scripts.run_miner \
  --subtensor.network finney \
  --wallet.name {your_wallet_name} \
  --wallet.hotkey {your_hotkey_name} \
  --netuid 73 \
  --axon.port {your_port} \
  --logging.debug
```

---

## Running a Validator

```bash
python -m merit.scripts.run_validator \
  --subtensor.network finney \
  --wallet.name {your_wallet_name} \
  --wallet.hotkey {your_hotkey_name} \
  --netuid 73 \
  --logging.debug
```

---

## Documentation

- 📄 [Whitepaper](./whitepaper.md)
- 🚀 [Roadmap](./roadmap.md)
- 🛠️ [Miner Setup Guide](./docs/miner_setup.md)
- 🛠️ [Validator Setup Guide](./docs/validator_setup.md)

---

## License

Distributed under the [MIT License](./LICENSE).

---

## Contributing

Contributions are welcome!  
Please review the `CONTRIBUTING.md` (coming soon) before submitting pull requests.

---

# End of Document
