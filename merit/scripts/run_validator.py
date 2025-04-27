import asyncio
from merit.neuron.validator import Validator

def main():
    validator = Validator()
    asyncio.run(validator.run())

if __name__ == "__main__":
    main()

