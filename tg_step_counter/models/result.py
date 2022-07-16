from datetime import datetime


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
