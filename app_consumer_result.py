import gspread
import logging
import nats
import os
import pickle

import asyncio
from telebot.async_telebot import AsyncTeleBot

from tg_step_counter.i18n import Internationalization as I18n

from tg_step_counter.message_parser import MessageParser

from tg_step_counter.objects.result import Result
from tg_step_counter.objects.tg_user import TGUser, TGUserSpreadsheetHandler


nats_address = os.environ.get("APP_NATS_ADDRESS", "nats://nats.nats.svc:4222")
nats_subject = os.environ.get("APP_NATS_SUBJECT", "common.>")

bot_token = os.environ.get("APP_TG_TOKEN")
bot = AsyncTeleBot(bot_token, parse_mode="Markdown")

google_service_account_fname = os.environ.get("APP_GOOGLE_SA_PATH", "./config/google-service-account.json")
google_sheet_uri = os.environ.get("APP_GOOGLE_SHEET_URI")

app_language = os.environ.get("APP_LANG", "en")
i18n = I18n(lang=app_language)


async def handler(message):
    global sheet

    logging.warning(f"Received a message on: {message.subject}")
    data = pickle.loads(message.data)

    logging.debug(data)

    message_parser = MessageParser()

    try:
        value = message_parser.get_value_from_reply(data.text)
    except ValueError:
        await bot.reply_to(data, "{webhook_error_parse_count}".format(**i18n.lang_map))
        return None

    date = message_parser.get_date_from_notify(data.reply_to_message.json.get("text"))

    result = Result(date_notation=date, value=value)

    tg_user = TGUser(id=data.from_user.id, username=data.from_user.username)
    tg_user_handler = TGUserSpreadsheetHandler(sheet, tg_user)

    tg_user_handler.touch()

    try:
        tg_user_handler.add_result(result)
    except gspread.exceptions.APIError as e:
        logging.error(f"Could not write results: {e}")
        await bot.reply_to(data, "{webhook_error_write_results}".format(**i18n.lang_map))
        return None

    monthly_sum = sum(tg_user_handler.get_monthly_map(result.month).values())
    monthly_sum_human = str(max(monthly_sum // 1000, 1)) + ",000"

    await bot.reply_to(
        data,
        "{webhook_results_written}".format(**i18n.lang_map).format(**{"monthly_sum_human": monthly_sum_human}),
    )


async def main():
    global sheet

    logging.warning(f"Getting Google Spreadsheet: {google_sheet_uri}")
    gc = gspread.service_account(filename=google_service_account_fname)
    sheet = gc.open_by_url(google_sheet_uri).sheet1

    logging.warning(f"Connecting to NATS at: {nats_address}")
    nc = await nats.connect(nats_address)

    logging.warning(f"Getting updates for subject: {nats_subject}")
    await nc.subscribe(nats_subject, cb=handler)
    # sub = await nc.subscribe(nats_subject, cb=handler)

    # TODO Unsub on exit
    # await sub.unsubscribe()
    # await nc.drain()

    # await asyncio.sleep(15)


if __name__ == "__main__":
    logging.critical("Starting consumer/result")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    try:
        loop.run_forever()
    finally:
        loop.close()
