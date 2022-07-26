import logging
import nats
import os
import pickle
import time

import asyncio
from telebot.async_telebot import AsyncTeleBot

from tg_step_counter.i18n import Internationalization as I18n


nats_address = os.environ.get("APP_NATS_ADDRESS", "nats://nats.nats.svc:4222")

bot_username = os.environ.get("APP_TG_USERNAME", "step_counter_dev_bot")

bot_token = os.environ.get("APP_TG_TOKEN")
bot = AsyncTeleBot(bot_token, parse_mode="Markdown")

app_language = os.environ.get("APP_LANG", "en")
i18n = I18n(lang=app_language)

# fmt: off
SUBJECT_PREFIXES = {
    "start": "common",
    "help": "common",
    "me": "stats",
    "add": "add",
    "leaderboard": "leaderboard",
}
# fmt: on


def filter_results_reply(message):
    if message.reply_to_message is None:
        return False

    if message.reply_to_message.json.get("text") is None:
        return False

    proper_user = message.reply_to_message.json.get("from").get("username") == bot_username
    proper_message = i18n.lang_map.reminder_mark in message.reply_to_message.json.get("text")

    return proper_user and proper_message


async def main():
    logging.warning(f"Connecting to NATS at {nats_address}")
    nc = await nats.connect(nats_address)

    @bot.message_handler(func=filter_results_reply)
    async def process_result(message):
        logging.warning(f"Processing message from {message.chat.id}")

        logging.debug(message)
        data = pickle.dumps(message)

        subject = f"result.{message.chat.id}"

        logging.warning(f"Sending message to subject {subject}")
        await nc.publish(subject, data)

    @bot.message_handler(func=lambda x: True)
    async def process_everything(message):
        logging.warning(f"Processing message from {message.chat.id}")

        logging.debug(message)
        data = pickle.dumps(message)

        command = f"not-a-command-{time.time()}"

        message_text = message.json.get("text")
        if message_text.startswith("/"):
            try:
                command = message_text.strip("/").split(" ").pop(0).split("@").pop(0)
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
