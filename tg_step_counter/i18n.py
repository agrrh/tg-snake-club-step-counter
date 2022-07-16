import logging
import yaml

from box import Box


class Internationalization(object):
    MAPS_PATH = "./i18n"

    def __init__(self, lang="en"):
        self.lang = lang

        self.__lang_map_load()

    def __lang_map_load(self):
        file_path = f"{self.MAPS_PATH}/{self.lang}.yml"

        try:
            fp = open(file_path, "r")
        except Exception as e:
            logging.error(f"Could not load file {file_path}: {e}")
            return False

        try:
            lang_data = yaml.load(fp, Loader=yaml.SafeLoader)
        except Exception as e:
            logging.error(f"Could not parse YAML from {file_path}: {e}")
            return False
        finally:
            fp.close()

        self.lang_map = Box(lang_data)
