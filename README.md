<div align="center">
<picture>
    <source srcset="icon48.png"  media="(prefers-color-scheme: dark)">
    <source srcset="icon48.png"  media="(prefers-color-scheme: light)">
    <img src="icon48.png">
</picture>

# **MetaHash Subnet (sn73)** <!-- omit in toc -->
[![Discord Chat](https://img.shields.io/discord/308323056592486420.svg)](https://discord.gg/bittensor)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Twitter Follow](https://img.shields.io/twitter/follow/MetaHashSubnet?style=social)](https://twitter.com/MetaHashSubnet)

[🌐 MetaHash Portal](https://metahash.io) • [🐦 Twitter](https://twitter.com/MetaHashSubnet) • [⛏️ Mining Guide](docs/miner.md) • [🧑‍🏫 Validator Guide](docs/validator.md)
</div>

---

## 🔍 Overview

**MetaHash** is a **liquidity-driven Bittensor subnet (sn73)** that unlocks over-the-counter (OTC) funding for miners while harvesting **high-value alpha** from every collaborating subnet.  
Think of it as **TaoHash for subnets**—but instead of purely trading TAO, we trade **liquidity for exclusive, non-public alpha** that we never resell.

- **For Miners:** Instantly access liquidity without dumping your own subnet tokens and depressing prices.  
- **For Validators & Holders:** Accumulate `$META` to tap into a continuous stream of cross-subnet alpha.  
- **For the Network:** Bootstrap healthy capital flow and cross-pollination of ideas, accelerating innovation across the entire Bittensor ecosystem.

## 🏗️ How MetaHash Works

1. **Liquidity Requests** – Miners from any subnet submit OTC liquidity requests to MetaHash validators.  
2. **Alpha Pledge** – In exchange, miners commit to share a portion of their freshly mined alpha (models, datasets, signals) at a negotiated discount.  
3. **Liquidity Provision** – MetaHash mints or transfers `$META` to the miner, providing immediate liquidity without open-market sell pressure on the miner’s native token.  
4. **Alpha Settlement** – Validators verify the delivered alpha and distribute it to `$META` holders via periodic on-chain releases.

> **Why a Discount?**  
> Miners receive capital up-front; MetaHash receives alpha at below-market cost. Both sides win while preserving price integrity on the miner’s home subnet.

## ⚙️ Subnet Mechanics

### 🧑‍🏫 Validator Role
- Review and price OTC liquidity requests.  
- Custody, evaluate and curate incoming alpha streams.  
- Distribute validated alpha drops to `$META` holders.  
- Assign weights on the **Bittensor Blockchain** based on timely and accurate alpha delivery.

### ⛏️ Miner Role
- Request liquidity through MetaHash’s OTC desk.  
- Provide high-quality, non-leaked alpha on schedule.  
- Continuously improve alpha quality to earn better terms and higher weights.

### 🎯 Incentive Mechanism

| Actor | Gives | Receives |
|-------|-------|----------|
| **Miner** | Future alpha (discounted) | Immediate `$META` liquidity |
| **Validator** | Liquidity + verification service | Stream of discounted alpha |
| **$META Holder** | Market demand for `$META` | Access to exclusive alpha drops |

- **Token:** `$META` (sn73 alpha)  
- **Utility:** Governance + access key to the alpha vault  
- **Demand Drivers:** Validators must hold `$META` to redeem alpha; traders accumulate to speculate on future unlocks.

## 🔄 OTC Deal Flow

```mermaid
flowchart LR
    Miner[Miner Subnet]
    Request>Liquidity Request]
    MetaHash[MetaHash Validators]
    Liquidity[$META Liquidity]
    Alpha[Alpha Stream]
    Holders[$META Holders]

    Miner -- Request --> MetaHash
    MetaHash -- Liquidity --> Miner
    Miner -- Alpha --> MetaHash
    MetaHash -- Curated Alpha --> Holders
