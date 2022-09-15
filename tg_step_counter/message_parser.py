import logging
import re


class MessageParser(object):
    """
    >>> mp = MessageParser()
    >>> mp.get_value_from_reply('100')
    100
    >>> mp.get_date_from_notify('hey 31.12 hey')
    '31.12'

    >>> mp.parse_add_message('10000')
    (10000, None)
    >>> mp.parse_add_message('12000 31.12')
    (12000, '31.12')
    >>> mp.parse_add_message('8000 15.09')
    (8000, '15.09')

    >>> mp.parse_add_message('31.12 12000')
    (12000, '31.12')
    >>> mp.parse_add_message('31.12 123')
    (123, '31.12')
    >>> mp.parse_add_message('11.09 8000')
    (8000, '11.09')
    """

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
            date = re.search(r"(?P<date>\d\d\.\d\d)", text).group("date")
            logging.debug(f"Parsed date {date} from text: {text}")
        except (AttributeError, ValueError):
            raise ValueError(f"Could not find date in message: {text}")

        return date

    def parse_add_message(self, text):
        text = text.strip()

        try:
            candidate = re.search(r"(?P<value>\d{3,6})", text)
            value = int(candidate.group("value"))
            logging.debug(f"Parsed value {value} from text: {text}")

        except (AttributeError, ValueError):
            raise ValueError(f"Could not find value in message: {text}")

        try:
            date = re.search(r"[0-9]{2}\.[0-9]{2}", text).group()
            logging.debug(f"Parsed date {date} from text: {text}")
        except (ValueError, AttributeError):
            logging.info(f"Could not find date in message: {text}")
            date = None

        return (value, date)
