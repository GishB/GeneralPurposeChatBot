import time
from datetime import datetime

import pytz


class ExecutionTimer:
    def __init__(self):
        self.start_time = time.perf_counter()

    def time(self):
        end_time = time.perf_counter()
        return end_time - self.start_time

    @staticmethod
    def get_msk_time() -> datetime:
        """Получить время в UTC+3 (Московское время)"""
        return datetime.now(pytz.timezone("Europe/Moscow"))

    @staticmethod
    def format_european_time(dt: datetime) -> str:
        """Форматировать в DD-MM-YYYY HH:MM:SS"""
        return dt.strftime("%d-%m-%Y %H:%M:%S")
