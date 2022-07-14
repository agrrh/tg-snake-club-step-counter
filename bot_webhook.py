import os
import logging
import re

from datetime import datetime

import telebot
import gspread

bot_token = os.environ.get("APP_TG_TOKEN")

google_service_account_fname = os.environ.get("APP_GOOGLE_SA_PATH", "./config/google-service-account.json")
google_sheet_uri = os.environ.get("APP_GOOGLE_SHEET_URI")

bot_username = os.environ.get("APP_TG_USERNAME", "step_counter_dev_bot")

bot = telebot.TeleBot(bot_token, parse_mode="Markdown")


def filter_results_reply(message):
    if message.reply_to_message is None:
        return False

    if message.reply_to_message.json.get("text") is None:
        return False

    proper_user = message.reply_to_message.json.get("from", {}).get("username") == bot_username
    proper_message = message.reply_to_message.json.get("text").startswith("⏰")

    return proper_user and proper_message


def parse_results(text):
    text = text.strip()

    try:
        value = int(text)
        return value
    except ValueError:
        logging.error("Could not convert message to integer")

    return False


def parse_notify(text):
    text = text.strip()

    try:
        date_ = re.search(r"[0-9]{2}\.[0-9]{2}", text).group()
        logging.debug(f"Parsed date {date_} from text: {text}")
    except ValueError:
        logging.error("Could not find date in message")
        return False

    return date_


def write_results(user_id, result_date, value, username=None):
    """
    TODO Rework as follows:

        sheet = get_spreadsheet()
        user_column_index = find_or_add_user()
        update_daily_result()
        update_monthly_result()
    """

    gc = gspread.service_account(filename=google_service_account_fname)
    sheet = gc.open_by_url(google_sheet_uri).sheet1

    logging.info(f"Writing value {value} for user {user_id}")

    users_row_index = 1

    users_row = sheet.get_values(f"{users_row_index}:{users_row_index}")[0]
    logging.debug(users_row)

    if not users_row:
        logging.error("Data seems to be empty")
        return False

    try:
        users_column_index = users_row.index(str(user_id)) + 1
    except ValueError:
        logging.warning(f"Could not find user {user_id}, adding new")

        users_column_index = len(users_row) + 1  # A is 1, B is 2, C is 3, ...
        sheet.update_cell(users_row_index, users_column_index, user_id)

        if username:
            user_cell = gspread.cell.Cell(users_row_index, users_column_index)
            sheet.update_note(user_cell.address, username)

    daily_range_start = 16
    daily_range_end = 382

    daily_row_index = daily_range_start + int(datetime.strptime(result_date, "%d.%m").strftime("%j"))

    sheet.update_cell(daily_row_index, 1, str(result_date))
    sheet.update_cell(daily_row_index, users_column_index, value)

    daily_range = sheet.get_values(f"{daily_range_start}:{daily_range_end}")

    result_month_humanized = result_date.split(".")[1]
    result_month = int(result_month_humanized)
    # fmt: off
    users_results = [
        (cell[0], cell[users_column_index - 1])
        for cell
        in daily_range
        if result_month_humanized in cell[0]
    ]
    # fmt: on

    # all results array
    logging.debug(users_results)

    # update monthly sum
    users_sum = sum([int(entry[1]) for entry in users_results])
    logging.debug(users_sum)
    sheet.update_cell(1 + result_month, users_column_index, users_sum)

    return users_sum


@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    bot.reply_to(message, "Howdy, how are you doing?")


@bot.message_handler(func=filter_results_reply)
def process_results_reply(message):
    logging.warning("Processing results reply")

    logging.debug(message)

    value = parse_results(message.text)
    result_date = parse_notify(message.reply_to_message.json.get("text"))

    if not value:
        bot.reply_to(
            message,
            "К сожалению, не могу найти число в вашем сообщении. Ответьте на исходное сообщение, указав только число шагов.",  # noqa
        )
        return None

    try:
        monthly_sum = write_results(message.from_user.id, result_date, value, username=message.from_user.username)
    except gspread.exceptions.APIError:
        monthly_sum = False
        logging.error("Could not write results")

    if not monthly_sum:
        bot.reply_to(message, "К сожалению, не смог записать результаты, попробуйте позже.")
        return None

    monthly_sum_humanized = max(monthly_sum // 1000, 1)

    bot.reply_to(
        message,
        f"Спасибо, результаты учтены, ваш общий результат за этот месяц около {monthly_sum_humanized} 000 шагов.",
    )


if __name__ == "__main__":
    logging.critical("Starting webhook")

    bot.infinity_polling()
