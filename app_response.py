import gspread
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

google_service_account_fname = os.environ.get("APP_GOOGLE_SA_PATH", "./config/google-service-account.json")
google_sheet_uri = os.environ.get("APP_GOOGLE_SHEET_URI")


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

    fp = open(photo, "rb")

    return await bot.send_photo(
        chat_id=chat_id,
        photo=fp,
        caption=caption,
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
    logging.warning(f"Getting Google Spreadsheet: {google_sheet_uri}")
    gc = gspread.service_account(filename=google_service_account_fname)
    sheet = gc.open_by_url(google_sheet_uri).sheet1

    logging.warning(f"Connecting to NATS at: {nats_address}")
    async with (await nats.connect(nats_address)) as nc:
        logging.warning(f"Getting updates for subject: {nats_subject}")
        sub = await nc.subscribe(nats_subject)

        while True:
            try:
                message = await sub.next_msg(timeout=60)
                await handler(message, sheet)
            except nats.errors.TimeoutError:
                pass
            except Exception as e:
                logging.error(f"Error during handling message: {e}")

        logging.warning("Moving past subscribe ...")


if __name__ == "__main__":
    logging.critical("Starting svc/response")

    asyncio.run(main())
