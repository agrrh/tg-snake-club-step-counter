import logging
import nats
import os
import pickle

import asyncio
from telebot.async_telebot import AsyncTeleBot


nats_address = os.environ.get("APP_NATS_ADDRESS", "nats://nats.nats.svc:4222")
nats_subject = os.environ.get("APP_NATS_SUBJECT", "response.>")

bot_token = os.environ.get("APP_TG_TOKEN")
bot = AsyncTeleBot(bot_token, parse_mode="Markdown")


async def send_message(**kwargs):
    chat_id = kwargs.get("chat_id")
    text = kwargs.get("text")

    return await bot.send_message(chat_id, text)


async def send_reply(**kwargs):
    message = kwargs.get("message")
    text = kwargs.get("text")

    return await bot.reply_to(message, text)


async def send_photo(**kwargs):
    chat_id = kwargs.get("chat_id")
    photo = kwargs.get("photo")
    caption = kwargs.get("text")
    reply_to = kwargs.get("reply_to")

    fp = open(photo, "rb")

    return await bot.send_photo(
        chat_id=chat_id,
        photo=fp,
        caption=caption,
        reply_to_message_id=reply_to,
    )


HANDLERS = {
    "generic": send_message,
    "reply": send_reply,
    "photo": send_photo,
}


async def handler(message):
    logging.warning(f"Received a message on: {message.subject}")
    data = pickle.loads(message.data)

    logging.debug(data)

    message_type = data.get("type") or "generic"

    message_handler = HANDLERS.get(message_type)

    await message_handler(**data)


async def main():
    logging.warning(f"Connecting to NATS at: {nats_address}")
    async with (await nats.connect(nats_address)) as nc:
        logging.warning(f"Getting updates for subject: {nats_subject}")
        sub = await nc.subscribe(nats_subject)

        while True:
            try:
                message = await sub.next_msg(timeout=60)
                await handler(message)
            except nats.errors.TimeoutError:
                pass
            except Exception as e:
                logging.error("Error during handling message")
                logging.exception(e)

        logging.warning("Moving past subscribe ...")


if __name__ == "__main__":
    logging.critical("Starting svc/response")

    asyncio.run(main())
