import bittensor as bt
import asyncio
from merit.neuron.validator import Validator

def main():
    parser = bt.ArgumentParser()
    parser.add_argument("--netuid", type=int, help="Subnet netuid to validate.")
    parser.add_argument("--ping_frequency", type=int, default=None, help="Optional ping frequency in seconds.")
    config = bt.config(parser=parser)
    bt.logging(config=config)

    validator = Validator(config=config)
    asyncio.run(validator.run())

if __name__ == "__main__":
    main()
