import gspread
import logging
import nats
import os
import redis
import pickle

import asyncio
from telebot.async_telebot import AsyncTeleBot

from tg_step_counter.i18n import Internationalization as I18n

from tg_step_counter.objects.result import Result, ResultPlot
from tg_step_counter.objects.tg_user import TGUser, TGUserSpreadsheetHandler


nats_address = os.environ.get("APP_NATS_ADDRESS", "nats://nats.nats.svc:4222")
nats_subject = os.environ.get("APP_NATS_SUBJECT", "logic")

bot_token = os.environ.get("APP_TG_TOKEN")
bot = AsyncTeleBot(bot_token, parse_mode="Markdown")

google_service_account_fname = os.environ.get("APP_GOOGLE_SA_PATH", "./config/google-service-account.json")
google_sheet_uri = os.environ.get("APP_GOOGLE_SHEET_URI")

redis_host = os.environ.get("APP_REDIS_HOST", "redis")
redis_handler = redis.StrictRedis(host=redis_host)

app_language = os.environ.get("APP_LANG", "en")
i18n = I18n(lang=app_language)

REDIS_TTL = int(os.environ.get("APP_REDIS_TTL", "86400"))


async def handler_stats(message, sheet, nats_handler=None):
    logging.warning(f"Received a message on: {message.subject}")
    data = pickle.loads(message.data)

    logging.debug(data)

    result_dummy = Result(date_notation=None)

    tg_user = TGUser(id=data.from_user.id)
    tg_user_handler = TGUserSpreadsheetHandler(sheet, tg_user)

    monthly_map = tg_user_handler.get_monthly_map(result_dummy.month)
    monthly_sum = sum(monthly_map.values())

    result_plot = ResultPlot()
    plot = result_plot.generate(monthly_map)
    fname = result_plot.save(plot, fname=str(data.from_user.id))

    chat_id = data.json.get("chat").get("id")

    text = "{webhook_results_monthly}".format(**i18n.lang_map).format(**{"monthly_sum": monthly_sum})

    reply_to = data.id

    with open(fname, "rb").read() as image_data:
        key = fname.split("/")[-1]
        redis_handler.setex(key, REDIS_TTL, image_data)

    message = {
        "type": "photo",
        "chat_id": chat_id,
        "photo": fname,
        "text": text,
        "reply_to": reply_to,
    }

    await nats_handler.publish(nats_subject, message)


async def main():
    logging.warning(f"Getting Google Spreadsheet: {google_sheet_uri}")
    gc = gspread.service_account(filename=google_service_account_fname)
    sheet = gc.open_by_url(google_sheet_uri).sheet1

    logging.warning(f"Connecting to NATS at: {nats_address}")
    async with (await nats.connect(nats_address)) as nc:
        logging.warning(f"Getting updates for subject: {nats_subject}")
        sub = await nc.subscribe(nats_subject, "workers")

        while True:
            try:
                message = await sub.next_msg(timeout=60)
                logging.warning(message)

                if message.subject.startswith("logic.stats"):
                    await handler_stats(message, sheet, nats_handler=nc)
            except nats.errors.TimeoutError:
                pass
            except Exception as e:
                logging.error(f"Error during handling message: {e}")
                logging.exception(e)

        logging.warning("Moving past subscribe ...")


if __name__ == "__main__":
    logging.critical("Starting svc/logic")

    asyncio.run(main())
