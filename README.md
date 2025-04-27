# Merit Subnet

Merit Subnet is a custom [Bittensor](https://docs.bittensor.com/) subnet that rewards miners based on their participation and performance across the Bittensor network.

---

## 📦 Project Structure

```
merit/
├── setup.py
├── requirements.txt
├── LICENSE
├── README.md
├── merit/
│   ├── __init__.py
│   ├── config/
│   │   └── merit_config.py
│   ├── protocol/
│   │   └── merit_protocol.py
│   ├── neuron/
│   │   ├── miner.py
│   │   └── validator.py
│   ├── scripts/
│   │   ├── run_miner.py
│   │   └── run_validator.py
│   ├── tests/
│   │   ├── test_protocol.py
│   │   └── test_bmps_calculation.py
└── epoch_results/ (auto-created)
```

---

## ⚙️ Installation

From the project root:

```bash
pip install .
```

Make sure your environment includes:
- `bittensor>=9.4.0`
- `pyotp>=2.8.0`

---

## 🚀 Running Miner

```bash
python -m merit.scripts.run_miner
```

- Miner listens for ping requests and responds with TOTP tokens.
- Axon server automatically binds to external IP and port.

---

## 🚀 Running Validator

```bash
python -m merit.scripts.run_validator
```

- Validator fetches Metagraph.
- Sends PingRequests to miners and validates TOTP responses.
- Calculates BMPS (Bittensor Miner Participation Score) based on incentive and ping success.
- Normalizes weights and submits them to the chain per epoch.
- Saves detailed JSON results every epoch.

---

## 🔍 Key Features

| Feature | Description |
|---------|-------------|
| **Ping Validation** | Verifies miners using pyotp TOTP tokens. |
| **BMPS Calculation** | Based on incentives across all subnets except netuid 0 and 73. |
| **Crash Recovery** | If validator crashes mid-epoch, resumes safely using `.merit_state.json`. |
| **Miner Health Tracking** | Persistent miner health score from 1.0 to 10.0 (rewards uptime and stability). |
| **Epoch Results** | JSON logs per epoch stored in `epoch_results/`. Only last 48 epochs kept. |
| **Auto-Cleanup** | Older epochs pruned automatically to save space. |

---

## ⚙️ Configuration

Edit `merit/config/merit_config.py` to adjust:

- `TEMPO`: Blocks per epoch (default 360).
- `PING_TIMEOUT`: Single ping timeout (default 10s).
- `PING_RETRIES`: Number of retries per miner (default 2).
- `HEALTH_INITIAL`, `HEALTH_MAX`, `HEALTH_INCREASE`, `HEALTH_DECREASE`: Health scoring system.
- `MAX_EPOCH_FILES`: Maximum number of epoch result JSONs to retain (default 48).
- `NETWORK`: Network name (default "finney").

---

## 🧪 Running Tests

```bash
python -m unittest discover merit/tests
```

Covers:
- PingRequest / PingResponse field integrity.
- Normalization of BMPS scoring.
- Protection against division-by-zero scenarios.

---

## 🛡️ License

MIT License.

---

