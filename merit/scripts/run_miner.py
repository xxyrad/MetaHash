import bittensor as bt
import asyncio
from merit.neuron.miner import Miner

def main():
    parser = bt.ArgumentParser()
    parser.add_argument("--netuid", type=int, help="Subnet netuid to mine on.")
    config = bt.config(parser=parser)
    bt.logging(config=config)

    miner = Miner(config=config)
    miner.run()

if __name__ == "__main__":
    main()
