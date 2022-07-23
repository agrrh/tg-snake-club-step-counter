import logging
import gspread

from tg_step_counter.objects.result import Result


class TGUser(object):
    """
    Doctests:

    >>> tg_user = TGUser(id=51)
    >>> tg_user.id
    51
    >>> tg_user.username is None
    True
    >>> len(tg_user.results)
    0
    """

    def __init__(self, id: int, username: str = None):
        self.id = id
        self.username = username

        self.results = []


class TGUserSpreadsheetHandler(object):
    USERS_ROW_INDEX = 1

    MONTHLY_ROW_START = 1

    DAILY_ROW_START = 16
    DAILY_ROW_END = 382

    def __init__(self, sheet: gspread.Worksheet, tg_user: TGUser):
        self._sheet = sheet

        self.tg_user = tg_user
        self.column_index = self.__get_column_index()

    def get_users_row(self) -> list:
        return self._sheet.get_values(f"{self.USERS_ROW_INDEX}:{self.USERS_ROW_INDEX}")[0]

    def get_user_note(self) -> str:
        cell = self._sheet.cell(self.USERS_ROW_INDEX, self.column_index)

        return self._sheet.get_note(cell.address)

    def __get_column_index(self) -> int:
        """
        Return column index as in spreadsheet.
            A is 1, B is 2, C is 3, ...
        """

        logging.debug(f"Getting column_index for {self.tg_user.id}")

        users_row = self.get_users_row()

        try:
            column_index = users_row.index(str(self.tg_user.id)) + 1
        except ValueError:
            return 0

        return column_index

    def __get_last_column_index(self) -> int:
        logging.debug("Getting last column index to add new user")

        users_row = self.get_users_row()

        return len(users_row) + 1

    @property
    def exists(self) -> bool:
        logging.debug(f"Checking if TG User {self.tg_user.id} entry exists")

        return self.column_index != 0

    def touch(self) -> bool:
        logging.info(f"Touching {self.tg_user.id}")

        if not self.exists:
            self.column_index = self.__get_last_column_index()
            self._sheet.update_cell(self.USERS_ROW_INDEX, self.column_index, self.tg_user.id)

        if self.tg_user.username:
            user_cell = self._sheet.cell(self.USERS_ROW_INDEX, self.column_index)
            self._sheet.update_note(user_cell.address, self.tg_user.username)

    def get_results(self) -> list[Result]:
        daily_range = self._sheet.get_values(f"{self.DAILY_ROW_START}:{self.DAILY_ROW_END}")

        results_list = []

        for cell in daily_range:
            date_notation = cell[0]
            value = cell[self.column_index - 1]
            logging.debug(f"date_notation is {date_notation}, value is {value}")

            if not (date_notation and value):
                continue

            r = Result(date_notation=date_notation, value=int(value))

            logging.debug(f"Adding {r} to monthly sum: {r.value} at {r.date_human}")

            results_list.append(r)

        self.tg_user.results = results_list

        return self.tg_user.results

    def add_result(self, result: Result) -> bool:
        this_row_index = self.DAILY_ROW_START + result.day_number_in_year

        # add daily entry
        self._sheet.update_cell(this_row_index, 1, result.date_human)
        self._sheet.update_cell(this_row_index, self.column_index, result.value)

        self.update_monthly(result.month)

    def get_monthly_map(self, month) -> dict:
        return {r.date_human: r.value for r in self.get_results() if r.month == month}

    def get_monthly(self, month) -> int:
        cell = self._sheet.cell(self.MONTHLY_ROW_START + month, self.column_index)

        return cell.numeric_value

    def update_monthly(self, month) -> None:
        monthly_sum = sum(self.get_monthly_map(month).values())

        # add monthly entry
        self._sheet.update_cell(self.MONTHLY_ROW_START + month, 1, month)
        self._sheet.update_cell(self.MONTHLY_ROW_START + month, self.column_index, monthly_sum)
