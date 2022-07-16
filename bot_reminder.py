import os
import sys
import time
import logging

from datetime import date, timedelta

import schedule
import telebot

from tg_step_counter.i18n import Internationalization as I18n


bot_token = os.environ.get("APP_TG_TOKEN")

bot = telebot.TeleBot(bot_token, parse_mode="Markdown")

chat_id = os.environ.get("APP_TG_CHAT_ID")
app_dev_mode = os.environ.get("APP_DEV_MODE")
challenge_tag = os.environ.get("APP_TG_CHALLENGE_TAG")

notify_time = os.environ.get("APP_TG_NOTIFY_TIME", "10:00")

app_language = os.environ.get("APP_LANG", "en")

i18n = I18n(lang=app_language)

# TODO Refactor as in example
#   https://github.com/eternnoir/pyTelegramBotAPI/blob/master/examples/timer_bot.py


def send_notify():
    logging.warning("Sending notify")

    # TODO Date calculations as separate function
    date_current = date.today()
    date_one_day_before = timedelta(days=-1)

    date_notify = date_current + date_one_day_before

    current_date_human = date_notify.strftime("%d.%m")

    # TODO Use single dynamic data map object for second format()
    notify_text = "{reminder_mark} {reminder_notify}".format(**i18n.lang_map).format(
        **{
            "challenge_tag": challenge_tag,
            "current_date_human": current_date_human,
        }
    )

    bot.send_message(chat_id, notify_text)

    return None


if __name__ == "__main__":
    logging.critical("Starting reminder")

    if app_dev_mode:
        logging.warning("Running single dev run")

        schedule.every(1).seconds.do(send_notify)
        time.sleep(1)
        schedule.run_pending()
        sys.exit()

    schedule.every().day.at(notify_time).do(send_notify)

    while True:
        schedule.run_pending()
        time.sleep(5)
