import os
import logging

import asyncio
import telebot

import pickle

import nats

nats_address = os.environ.get("APP_NATS_ADDRESS", "http://nats.nats:4222")

bot_token = os.environ.get("APP_TG_TOKEN")

bot = telebot.TeleBot(bot_token, parse_mode="Markdown")


async def main():
    logging.warning(f"Connecting to NATS at {nats_address}")
    nc = await nats.connect(nats_address)

    @bot.message_handler(func=lambda x: True)
    def process_update(message):
        logging.warning(message)

        chat_id = message.chat.id

        logging.warning(f"Processing message from {chat_id}")

        data = pickle.dumps(message.message)

        await nc.publish(f"chat.{chat_id}", data)

    logging.warning("Getting updates")
    bot.polling()

    logging.warning("Continue getting updates ...")


if __name__ == "__main__":
    logging.critical("Starting tg-nats producer")

    asyncio.run(main())
