import os
import logging

import asyncio

import pickle

import nats

nats_address = os.environ.get("APP_NATS_ADDRESS", "nats://nats.nats.svc:4222")


async def handler(message):
    logging.warning(f'Received a message on "{message.subject} {message.reply}"')
    data = pickle.loads(message)

    logging.debug(data)


async def main():
    logging.warning(f"Connecting to NATS at {nats_address}")
    nc = await nats.connect(nats_address)

    logging.warning('Getting updates for subject "common"')
    sub = await nc.subscribe("common.>")

    try:
        async for message in sub.messages:
            await handler(message)
            await sub.unsubscribe()
    except Exception as e:
        logging.error(f"Error during message handling: {e}")


if __name__ == "__main__":
    logging.critical("Starting tg-nats consumer")

    asyncio.run(main())
