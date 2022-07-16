import logging

from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np


class Result(object):
    """
    Doctests:

    >>> result = Result(date_notation="16.08")

    >>> result.date
    datetime.datetime(1900, 8, 16, 0, 0)
    >>> result.value
    0
    >>> result.day
    16
    >>> result.month
    8
    >>> result.day_number_in_year
    228
    """

    def __init__(
        self,
        date_notation: str = "01.01",
        value: int = 0,
        date: datetime = datetime.today(),
    ):
        self.date = self.__parse_date_notation(date_notation) if date_notation else date
        self.value = value

    def __parse_date_notation(self, notation: str) -> datetime:
        return datetime.strptime(notation, "%d.%m")

    @property
    def date_human(self) -> str:
        return self.date.strftime("%d.%m")

    @property
    def day(self) -> int:
        return int(self.date.strftime("%d"))

    @property
    def month(self) -> int:
        return int(self.date.strftime("%m"))

    @property
    def day_number_in_year(self) -> int:
        return int(self.date.strftime("%j"))


class ResultPlot(object):
    def __init__(self, save_dir="/tmp"):
        self.save_dir = save_dir

    def __monthly_map_to_list(self, monthly_map):
        def list_replace(list_, i, v):
            list_.pop(i)
            list_.insert(i, v)

        monthly_list = [0] * 31

        [list_replace(monthly_list, int(k.split(".")[0]) - 1, v) for k, v in monthly_map.items()]

        return monthly_list

    def my_stat(self, data) -> plt:
        logging.warning("Generating monthly stats plot")

        plt.style.use("_mpl-gallery")

        x = 0.5 + np.arange(31)
        y = self.__monthly_map_to_list(data)

        xlim = (0, 31)
        ylim = (0, max(y) * 1.2)

        ystep = min([100, 500, 1000, 2500, 5000, 10000], key=lambda x: abs(x - max(y) * 0.3))

        xticks = np.arange(1, 31, 7)
        yticks = np.arange(0, max(y) * 1.2, ystep)

        fig, ax = plt.subplots()

        fig.set_size_inches(8, 4.5)
        fig.set_dpi(60)

        ax.set_title("Monthly summary")
        ax.set_xlabel("Days")
        ax.set_ylabel("Steps")

        ax.bar(x, y, width=1, edgecolor="white", linewidth=0.7, antialiased=True)
        ax.set(xlim=xlim, xticks=xticks, ylim=ylim, yticks=yticks)

        fig.tight_layout()

        return plt

    def save(self, plt: plt, fname: str = "changeme") -> str:
        fname = f"{self.save_dir}/{fname}.png"

        plt.savefig(fname, format="png", pad_inches=0.5)

        return fname
