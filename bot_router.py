import os
import logging

import asyncio
from telebot.async_telebot import AsyncTeleBot

import pickle

import nats

from collections import defaultdict


nats_address = os.environ.get("APP_NATS_ADDRESS", "nats://nats.nats.svc:4222")

bot_token = os.environ.get("APP_TG_TOKEN")

bot = AsyncTeleBot(bot_token, parse_mode="Markdown")

# fmt: off
SUBJECT_PREFIXES = defaultdict(lambda: "null")
SUBJECT_PREFIXES.update({
    "start": "common",
    "help": "common",
    "me": "stats"
})
# fmt: on


async def main():
    logging.warning(f"Connecting to NATS at {nats_address}")
    nc = await nats.connect(nats_address)

    @bot.message_handler(func=lambda x: True)
    async def process_update(message):
        logging.warning(f"Processing message from {message.chat.id}")

        data = pickle.dumps(message)

        subject_prefix = SUBJECT_PREFIXES.get(message.command)

        await nc.publish(f"{subject_prefix}.{message.chat.id}", data)

    logging.warning("Getting updates")
    await bot.polling()


if __name__ == "__main__":
    logging.critical("Starting tg-nats producer")

    asyncio.run(main())
