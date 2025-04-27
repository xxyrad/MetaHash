# Merit Subnet - WHITEPAPER

---

## Believe

Merit is a Bittensor subnet (NetUID 73) designed to reward miner participation across the broader Bittensor ecosystem.  
Validators on Merit assess registered miners' performance in other subnets, measure their active participation, and assign emissions based on their relative contributions.  
Merit aims to create a fair, secure, and scalable participation-based incentive layer across all Bittensor subnets.

---

## Purpose

- Incentivize **cross-subnet participation** by miners.
- Reward miners who demonstrate **consistent uptime** and **positive incentives** elsewhere.
- Protect the Merit subnet from **fake, non-compliant**, or **idle miners** through **strict validation** mechanisms.

---

## Validator Design

Validators on Merit operate under the following architecture:

- **Metagraph Synchronization**:  
  Regularly fetch the full Metagraph of subnet 73.
  
- **Neuron-Based Filtering**:  
  Validators only consider miners by inspecting each `NeuronInfoLite`:
  - Skip if `validator_permit == True`
  - Skip if `dividends > 0`
  - Skip if `validator_trust > 0`
  
- **Incentive Calculation**:
  - Average the miner’s incentive across all **other subnets**.
  - **Ignore** Merit’s own NetUID (73) and NetUID 0.
  - **Scale** incentive ×1000 to give it greater weight.
  
- **Uptime Bonus**:
  - +1.0 point for successful ping per epoch.
  - -0.25 points for failed ping per epoch (after validation).
  
- **Weight Normalization**:
  - Miner scores are normalized to produce valid Bittensor weights.

- **Epoch Historical Data**:
  - Retain only the last 48 epochs of scoring data for historical purposes.

---

## Security and Miner Validation

Validators employ strict validation procedures:

- **TCP Preflight Check**:
  - Before pinging, validators perform a lightweight TCP connection check to ensure the miner's IP:PORT is reachable.
  
- **Strict Ping Validation**:
  - Only accept responses matching the `PingResponse` format.
  - Verify presence and integrity of the TOTP token.
  - Use the miner’s hotkey as the TOTP seed.
  - Accept only if TOTP token matches the current or previous valid window.
  
- **Hard Failures**:
  - Any unexpected response type, missing token, invalid token, or unreachable miner leads to a failed ping.
  - No partial credits are awarded for "partial" responses.

---

## Emissions Design

| Factor | Weight |
|--------|--------|
| Cross-subnet Incentive | 90% of BMPS score |
| Subnet Uptime (Ping Success) | 10% of BMPS score |

✅ The system prioritizes **real-world contribution** to Bittensor first, with **uptime reliability** as a secondary bonus.

---
## Merit: Core Values

- **Fairness**: Emissions are earned, not given.
- **For Miners by Miner**: Merit empowers miners supporting the entire Bittensor network.

---
## Merit: Roadmap
- **Fairness**: Emissions are earned, not given.
- **For Miners by Miner**: Merit empowers miners supporting the entire Bittensor network.

---
# End of Document
