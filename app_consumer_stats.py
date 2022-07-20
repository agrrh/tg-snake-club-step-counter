import gspread
import logging
import nats
import os
import pickle

import asyncio
from telebot.async_telebot import AsyncTeleBot

from tg_step_counter.i18n import Internationalization as I18n

from tg_step_counter.objects.result import Result, ResultPlot
from tg_step_counter.objects.tg_user import TGUser, TGUserSpreadsheetHandler


nats_address = os.environ.get("APP_NATS_ADDRESS", "nats://nats.nats.svc:4222")
nats_subject = os.environ.get("APP_NATS_SUBJECT", "stats.>")

bot_token = os.environ.get("APP_TG_TOKEN")
bot = AsyncTeleBot(bot_token, parse_mode="Markdown")

google_service_account_fname = os.environ.get("APP_GOOGLE_SA_PATH", "./config/google-service-account.json")
google_sheet_uri = os.environ.get("APP_GOOGLE_SHEET_URI")

app_language = os.environ.get("APP_LANG", "en")
i18n = I18n(lang=app_language)


async def handler(message, sheet):
    logging.warning(f"Received a message on: {message.subject}")
    data = pickle.loads(message.data)

    logging.debug(data)

    result_dummy = Result(date_notation=None)

    tg_user = TGUser(id=data.from_user.id, username=data.from_user.username)
    tg_user_handler = TGUserSpreadsheetHandler(sheet, tg_user)

    monthly_map = tg_user_handler.get_monthly_map(result_dummy.month)
    monthly_sum = sum(monthly_map.values())

    result_plot = ResultPlot()
    plot = result_plot.my_stat(monthly_map)
    fname = result_plot.save(plot, fname=str(data.from_user.id))

    with open(fname, "rb") as fp:
        bot.send_photo(
            chat_id=data.json.get("chat").get("id"),
            photo=fp,
            caption="{webhook_results_monthly}".format(**i18n.lang_map).format(**{"monthly_sum": monthly_sum}),
            reply_to_message_id=data.id,
        )

    await bot.reply_to(data, i18n.lang_map.help_reply)


async def main():
    logging.warning(f"Connecting to NATS at: {nats_address}")
    nc = await nats.connect(nats_address)

    logging.warning(f"Getting updates for subject: {nats_subject}")
    sub = await nc.subscribe(nats_subject)

    logging.warning(f"Getting Google Spreadsheet: {google_sheet_uri}")
    gc = gspread.service_account(filename=google_service_account_fname)
    sheet = gc.open_by_url(google_sheet_uri).sheet1

    try:
        async for message in sub.messages:
            await handler(message, sheet)
    except Exception as e:
        logging.error(f"Error during message handling: {e}")

    await sub.unsubscribe()
    await nc.drain()


if __name__ == "__main__":
    logging.critical("Starting consumer/common")

    asyncio.run(main())
