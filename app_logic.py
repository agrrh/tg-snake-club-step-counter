import aiofiles
import asyncio
import gspread
import logging
import nats
import os
import pickle
import redis

from tg_step_counter.message_parser import MessageParser

from tg_step_counter.i18n import Internationalization as I18n

from tg_step_counter.objects.result import Result, ResultPlot
from tg_step_counter.objects.leaderboard import LeaderboardPlot
from tg_step_counter.objects.tg_user import TGUser, TGUserSpreadsheetHandler


nats_address = os.environ.get("APP_NATS_ADDRESS", "nats://nats.nats.svc:4222")
nats_subject = os.environ.get("APP_NATS_SUBJECT", "logic")
nats_subject_response = os.environ.get("APP_NATS_SUBJECT_RESPONSE", "response")

google_service_account_fname = os.environ.get("APP_GOOGLE_SA_PATH", "./config/google-service-account.json")
google_sheet_uri = os.environ.get("APP_GOOGLE_SHEET_URI")

redis_host = os.environ.get("APP_REDIS_HOST", "redis")
redis_handler = redis.StrictRedis(host=redis_host)

app_language = os.environ.get("APP_LANG", "en")
i18n = I18n(lang=app_language)

REDIS_TTL = int(os.environ.get("APP_REDIS_TTL", "86400"))


async def handler_leaderboard(message, sheet, nats_handler=None):
    logging.warning(f"Received a message on: {message.subject}")
    data = pickle.loads(message.data)

    logging.debug(data)

    result_dummy = Result(date_notation=None)

    tg_user = TGUser(id=data.from_user.id)
    tg_user_handler = TGUserSpreadsheetHandler(sheet, tg_user)

    logging.debug("Form users leaderboard map")

    monthly_sum_by_user = {}
    user_aliases = {}

    for tg_user_id in tg_user_handler.get_users_row():
        if not tg_user_id.isnumeric():
            continue

        _tg_user = TGUser(id=tg_user_id)
        _tg_user_handler = TGUserSpreadsheetHandler(sheet, _tg_user)

        monthly_sum_by_user[tg_user_id] = _tg_user_handler.get_monthly(result_dummy.month)
        user_aliases[tg_user_id] = _tg_user_handler.get_user_note()

    logging.debug(f"Resulting map: {monthly_sum_by_user}")

    result_plot = LeaderboardPlot()
    plot = result_plot.generate(monthly_sum_by_user, user_aliases)
    fname = result_plot.save(plot, fname=str(data.chat.id))

    leader_id = max(monthly_sum_by_user, key=monthly_sum_by_user.get)
    leader_value = max(monthly_sum_by_user.values())

    _tg_user = TGUser(id=leader_id)
    _tg_user_handler = TGUserSpreadsheetHandler(sheet, _tg_user)
    leader_alias = _tg_user_handler.get_user_note()

    chat_id = data.json.get("chat").get("id")
    text = "{webhook_leaderboard_moment}".format(**i18n.lang_map).format(
        **{"leader": leader_alias or leader_id, "leader_value": leader_value}
    )
    reply_to = data.id

    logging.warning(f"Opening file in async way: {fname}")
    async with aiofiles.open(fname, "rb") as afp:
        image_data = await afp.read()

    logging.warning("Sending file data to redis")
    redis_handler.set(fname, image_data)
    redis_handler.expire(fname, REDIS_TTL)

    message = {
        "type": "photo",
        "chat_id": chat_id,
        "photo": fname,
        "text": text,
        "reply_to": reply_to,
    }
    data = pickle.dumps(message)

    nats_subject = f"{nats_subject_response}.{chat_id}"

    logging.warning(f"Sending response message to bus: {nats_subject}")
    await nats_handler.publish(nats_subject, data)


async def handler_add(message, sheet, nats_handler=None):
    logging.warning(f"Received a message on: {message.subject}")
    data = pickle.loads(message.data)

    logging.debug(data)

    chat_id = data.json.get("chat").get("id")
    nats_subject = f"{nats_subject_response}.{chat_id}"

    message = {
        "type": "reply",
        "message": data,
        "text": None,
    }

    message_parser = MessageParser()

    try:
        value, date = message_parser.parse_add_message(data.text)
    except ValueError:
        message["text"] = "{add_parse_error}".format(**i18n.lang_map)
        data = pickle.dumps(message)
        await nats_handler.publish(nats_subject, data)
        return None

    result = Result(date_notation=date, value=value)

    if result.in_future:
        message["text"] = "{add_future_error}".format(**i18n.lang_map)
        data = pickle.dumps(message)
        await nats_handler.publish(nats_subject, data)
        return None

    user_alias = data.from_user.username or f"{data.from_user.first_name} {data.from_user.last_name}"

    tg_user = TGUser(id=data.from_user.id, alias=user_alias)
    tg_user_handler = TGUserSpreadsheetHandler(sheet, tg_user)

    tg_user_handler.touch()

    try:
        tg_user_handler.add_result(result)
    except gspread.exceptions.APIError as e:
        logging.error("Could not write results")
        logging.exception(e)
        message["text"] = "{webhook_error_write_results}".format(**i18n.lang_map)
        data = pickle.dumps(message)
        await nats_handler.publish(nats_subject, data)
        return None

    monthly_sum = sum(tg_user_handler.get_monthly_map(result.month).values())
    monthly_sum_human = str(max(monthly_sum // 1000, 1)) + ",000"

    message["text"] = "{webhook_results_written}".format(**i18n.lang_map).format(
        **{"monthly_sum_human": monthly_sum_human}
    )
    data = pickle.dumps(message)
    await nats_handler.publish(nats_subject, data)


async def handler_help(message, nats_handler=None):
    logging.warning(f"Received a message on: {message.subject}")
    data = pickle.loads(message.data)

    logging.debug(data)

    chat_id = data.json.get("chat").get("id")
    nats_subject = f"{nats_subject_response}.{chat_id}"

    message = {
        "type": "reply",
        "message": data,
        "text": i18n.lang_map.help_reply,
    }

    data = pickle.dumps(message)

    logging.warning(f"Sending response message to bus: {nats_subject}")
    await nats_handler.publish(nats_subject, data)


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

    logging.warning(f"Opening file in async way: {fname}")
    async with aiofiles.open(fname, "rb") as afp:
        image_data = await afp.read()

    logging.warning("Sending file data to redis")
    redis_handler.set(fname, image_data)
    redis_handler.expire(fname, REDIS_TTL)

    message = {
        "type": "photo",
        "chat_id": chat_id,
        "photo": fname,
        "text": text,
        "reply_to": reply_to,
    }
    data = pickle.dumps(message)

    nats_subject = f"{nats_subject_response}.{chat_id}"

    logging.warning(f"Sending response message to bus: {nats_subject}")
    await nats_handler.publish(nats_subject, data)


async def handler_result(message, sheet, nats_handler=None):
    logging.warning(f"Received a message on: {message.subject}")
    data = pickle.loads(message.data)

    logging.debug(data)

    message_parser = MessageParser()

    chat_id = data.json.get("chat").get("id")
    nats_subject = f"{nats_subject_response}.{chat_id}"

    message = {
        "type": "reply",
        "message": data,
        "text": None,
    }

    try:
        value = message_parser.get_value_from_reply(data.text)
    except ValueError:
        message["text"] = "{webhook_error_parse_count}".format(**i18n.lang_map)
        data = pickle.dumps(message)
        await nats_handler.publish(nats_subject, data)
        return None

    date = message_parser.get_date_from_notify(data.reply_to_message.json.get("text"))

    result = Result(date_notation=date, value=value)

    user_alias = data.from_user.username or f"{data.from_user.first_name} {data.from_user.last_name}"

    tg_user = TGUser(id=data.from_user.id, alias=user_alias)
    tg_user_handler = TGUserSpreadsheetHandler(sheet, tg_user)

    tg_user_handler.touch()

    try:
        tg_user_handler.add_result(result)
    except gspread.exceptions.APIError as e:
        logging.error(f"Could not write results: {e}")
        message["text"] = "{webhook_error_write_results}".format(**i18n.lang_map)
        data = pickle.dumps(message)
        await nats_handler.publish(nats_subject, data)
        return None

    monthly_sum = sum(tg_user_handler.get_monthly_map(result.month).values())
    monthly_sum_human = str(max(monthly_sum // 1000, 1)) + ",000"

    message["text"] = "{webhook_results_written}".format(**i18n.lang_map).format(
        **{"monthly_sum_human": monthly_sum_human}
    )
    data = pickle.dumps(message)

    logging.warning(f"Sending response message to bus: {nats_subject}")
    await nats_handler.publish(nats_subject, data)


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
                elif message.subject.startswith("logic.result"):
                    await handler_result(message, sheet, nats_handler=nc)
                elif message.subject.startswith("logic.help"):
                    await handler_help(message, nats_handler=nc)
                elif message.subject.startswith("logic.add"):
                    await handler_add(message, sheet, nats_handler=nc)
                elif message.subject.startswith("logic.leaderboard"):
                    await handler_leaderboard(message, sheet, nats_handler=nc)

            except nats.errors.TimeoutError:
                pass
            except Exception as e:
                logging.error("Error during handling message")
                logging.exception(e)

        logging.warning("Moving past subscribe ...")


if __name__ == "__main__":
    logging.critical("Starting svc/logic")

    asyncio.run(main())
