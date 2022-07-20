import logging
import nats
import os
import pickle
import time

import asyncio
from telebot.async_telebot import AsyncTeleBot


nats_address = os.environ.get("APP_NATS_ADDRESS", "nats://nats.nats.svc:4222")

bot_token = os.environ.get("APP_TG_TOKEN")
bot = AsyncTeleBot(bot_token, parse_mode="Markdown")

# fmt: off
SUBJECT_PREFIXES = {
    "start": "common",
    "help": "common",
    "me": "stats"
}
# fmt: on


async def main():
    logging.warning(f"Connecting to NATS at {nats_address}")
    nc = await nats.connect(nats_address)

    @bot.message_handler(func=lambda x: True)
    async def process_update(message):
        logging.warning(f"Processing message from {message.chat.id}")

        logging.warning(message)
        data = pickle.dumps(message)

        command = f"not-a-command-{time.time()}"

        message_text = message.json.get("text")
        if message_text.startswith("/"):
            try:
                command = message_text.strip("/").split("@").pop(0)
            except Exception as e:
                logging.error(f"Could not get command from message text: {message_text}")
                logging.error(e)

        logging.warning(command)

        subject_prefix = SUBJECT_PREFIXES.get(command, "null")
        subject = f"{subject_prefix}.{message.chat.id}"

        logging.warning(f"Sending message to subject {subject}")
        await nc.publish(subject, data)

    logging.warning("Getting updates")
    await bot.infinity_polling(timeout=60)


if __name__ == "__main__":
    logging.critical("Starting router")

    asyncio.run(main())
