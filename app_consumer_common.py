import os
import logging

import asyncio

import pickle

import nats

nats_address = os.environ.get("APP_NATS_ADDRESS", "nats://nats.nats.svc:4222")
nats_subject = os.environ.get("APP_NATS_SUBJECT", "common.>")


async def handler(message):
    logging.warning(f'Received a message on "{message.subject} {message.reply}"')
    data = pickle.loads(message.data.decode())

    logging.debug(data)


async def main():
    logging.warning(f"Connecting to NATS at: {nats_address}")
    nc = await nats.connect(nats_address)

    logging.warning(f"Getting updates for subject: {nats_subject}")
    sub = await nc.subscribe(nats_subject)

    try:
        async for message in sub.messages:
            await handler(message)
    except Exception as e:
        logging.error(f"Error during message handling: {e}")

    await sub.unsubscribe()
    await nc.drain()


if __name__ == "__main__":
    logging.critical("Starting tg-nats consumer")

    asyncio.run(main())
