import gspread
import logging
import nats
import os
import pickle

import asyncio
from telebot.async_telebot import AsyncTeleBot

from tg_step_counter.i18n import Internationalization as I18n

from tg_step_counter.objects.result import Result
from tg_step_counter.objects.leaderboard import LeaderboardPlot
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

    logging.debug("Form users leaderboard map")

    monthly_sum_by_user = {}

    for tg_user_id in tg_user_handler.get_users_row():
        if not tg_user_id.isnumeric():
            continue

        _tg_user = TGUser(id=tg_user_id)
        _tg_user_handler = TGUserSpreadsheetHandler(sheet, _tg_user)

        monthly_sum_by_user[tg_user_id] = _tg_user_handler.get_monthly(result_dummy.month)

    logging.debug(f"Resulting map: {monthly_sum_by_user}")

    result_plot = LeaderboardPlot()
    plot = result_plot.generate(monthly_sum_by_user)
    fname = result_plot.save(plot, fname=str(data.chat.id))

    leader = max(monthly_sum_by_user, key=monthly_sum_by_user.get)
    leader_value = max(monthly_sum_by_user.values())

    with open(fname, "rb") as fp:
        await bot.send_photo(
            chat_id=data.json.get("chat").get("id"),
            photo=fp,
            caption="{webhook_leaderboard_monthly}".format(**i18n.lang_map).format(
                **{"leader": leader, "leader_value": leader_value}
            ),
            reply_to_message_id=data.id,
        )


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
    logging.critical("Starting consumer/leaderboard")

    asyncio.run(main())
