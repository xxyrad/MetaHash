import argparse
import asyncio
from merit.neuron.validator import Validator

def main():
    parser = argparse.ArgumentParser(description="Run Merit Validator")

    parser.add_argument("--subtensor_network", type=str, default="finney",
                        help="Subtensor network name or endpoint URL (default: finney)")
    parser.add_argument("--wallet_name", type=str, required=True,
                        help="Name of the wallet to use")
    parser.add_argument("--wallet_hotkey", type=str, required=True,
                        help="Name of the hotkey to use")
    parser.add_argument("--netuid", type=int, required=True,
                        help="Subnet UID where the validator will operate")
    parser.add_argument("--ping_frequency", type=int, default=None,
                        help="Optional: Background ping frequency in seconds (default: None for no background pinging)")

    args = parser.parse_args()

    validator = Validator(
        network=args.subtensor_network,
        wallet_name=args.wallet_name,
        wallet_hotkey=args.wallet_hotkey,
        netuid=args.netuid,
        ping_frequency=args.ping_frequency,
    )

    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(validator.run())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
