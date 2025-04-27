import argparse
from merit.neuron.miner import Miner

def main():
    parser = argparse.ArgumentParser(description="Run Merit Miner")
    parser.add_argument("--subtensor_network", type=str, default="finney", help="Subtensor network name or endpoint URL")
    parser.add_argument("--wallet_name", type=str, required=True, help="Wallet name")
    parser.add_argument("--wallet_hotkey", type=str, required=True, help="Wallet hotkey")
    parser.add_argument("--netuid", type=int, required=True, help="Network UID")

    args = parser.parse_args()

    miner = Miner(
        network=args.subtensor_network,
        wallet_name=args.wallet_name,
        wallet_hotkey=args.wallet_hotkey,
        netuid=args.netuid,
    )
    miner.run()

if __name__ == "__main__":
    main()
