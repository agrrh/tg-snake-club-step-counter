import logging

import matplotlib.pyplot as plt
import numpy as np


class LeaderboardPlot(object):
    def __init__(self, save_dir="/tmp"):
        self.save_dir = save_dir

    def __monthly_map_to_list(self, monthly_map):
        def list_replace(list_, i, v):
            list_.pop(i)
            list_.insert(i, v)

        monthly_list = [0] * 31

        [list_replace(monthly_list, int(k.split(".")[0]) - 1, v) for k, v in monthly_map.items()]

        return monthly_list

    def generate(self, data) -> plt:
        logging.warning("Generating monthly leaderboard plot")

        plt.style.use("_mpl-gallery")

        users_number = len(data.keys())

        x = 0.5 + np.arange(users_number)
        y = data.values()

        xlim = (0, users_number)
        ylim = (0, max(y) * 1.2)

        ystep = min([1000, 2500, 5000, 10000, 25000, 50000], key=lambda x: abs(x - max(y) * 0.3))

        xticks = np.arange(1, users_number)
        yticks = np.arange(0, max(y) * 1.2, ystep)

        fig, ax = plt.subplots()

        fig.set_size_inches(8, 4.5)
        fig.set_dpi(60)

        ax.set_title("Monthly summary")
        ax.set_xlabel("Users")
        ax.set_ylabel("Steps sum")

        ax.bar(x, y, width=1, edgecolor="white", linewidth=0.7, antialiased=True)
        ax.set(xlim=xlim, xticks=xticks, ylim=ylim, yticks=yticks)

        fig.tight_layout()

        return plt

    def save(self, plt: plt, fname: str = "changeme") -> str:
        fname = f"{self.save_dir}/{fname}.png"

        plt.savefig(fname, format="png", pad_inches=0.5)

        return fname
