import os
import sys
import time
import logging

from datetime import date, timedelta

import schedule
import telebot


bot_token = os.environ.get("APP_TG_TOKEN")

bot = telebot.TeleBot(bot_token, parse_mode="Markdown")

chat_id = os.environ.get("APP_TG_CHAT_ID")
app_dev_mode = os.environ.get("APP_DEV_MODE")
challenge_tag = os.environ.get("APP_TG_CHALLENGE_TAG")

notify_time = os.environ.get("APP_TG_NOTIFY_TIME", "10:00")


def send_notify():
    logging.warning("Sending notify")

    date_current = date.today()
    date_one_day_before = timedelta(days=-1)

    date_notify = date_current + date_one_day_before

    current_date_humanized = date_notify.strftime("%d.%m")

    notify_text = f"⏰ Чтобы внести свои результаты по {challenge_tag} за {current_date_humanized}, отправьте число шагов ответом на это сообщение."  # noqa

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
