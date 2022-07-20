import logging
import nats
import os
import pickle

import asyncio
from telebot.async_telebot import AsyncTeleBot


nats_address = os.environ.get("APP_NATS_ADDRESS", "nats://nats.nats.svc:4222")
nats_subject = os.environ.get("APP_NATS_SUBJECT", "common.>")

bot_token = os.environ.get("APP_TG_TOKEN")
bot = AsyncTeleBot(bot_token, parse_mode="Markdown")


async def handler(message):
    logging.warning(f"Received a message on: {message.subject}")
    data = pickle.loads(message.data)

    logging.debug(data)

    await bot.reply_to(data, "Howdy, how are you doing?")


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
