import logging
import re


class MessageParser(object):
    def __init__(self):
        pass

    def get_value_from_reply(self, text):
        text = text.strip()

        try:
            value = int(text)
            logging.debug(f"Parsed value {value} from text: {text}")
        except ValueError:
            raise ValueError(f"Could not convert data to integer value: {text}")

        return value

    def get_date_from_notify(self, text):
        text = text.strip()

        try:
            date = re.search(r"[0-9]{2}\.[0-9]{2}", text).group()
            logging.debug(f"Parsed date {date} from text: {text}")
        except ValueError:
            raise ValueError(f"Could not find date in message: {text}")

        return date
