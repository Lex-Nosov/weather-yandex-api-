# -*- coding: utf-8 -*-

# В очередной спешке, проверив приложение с прогнозом погоды, вы выбежали
# навстречу ревью вашего кода, которое ожидало вас в офисе.
# И тут же день стал хуже - вместо обещанной облачности вас встретил ливень.

# Вы промокли, настроение было испорчено, и на ревью вы уже пришли не в духе.
# В итоге такого сокрушительного дня вы решили написать свою программу для прогноза погоды
# из источника, которому вы доверяете.

# Для этого вам нужно:

# Создать модуль-движок с классом WeatherMaker, необходимым для получения и формирования предсказаний.
# В нём должен быть метод, получающий прогноз с выбранного вами сайта (парсинг + re) за некоторый диапазон дат,
# а затем, получив данные, сформировать их в словарь {погода: Облачная, температура: 10, дата:datetime...}

# Добавить класс ImageMaker.
# Снабдить его методом рисования открытки
# (использовать OpenCV, в качестве заготовки брать lesson_016/python_snippets/external_data/probe.jpg):
#   С текстом, состоящим из полученных данных (пригодится cv2.putText)
#   С изображением, соответствующим типу погоды
# (хранятся в lesson_016/python_snippets/external_data/weather_img ,но можно нарисовать/добавить свои)
#   В качестве фона добавить градиент цвета, отражающего тип погоды
# Солнечно - от желтого к белому
# Дождь - от синего к белому
# Снег - от голубого к белому
# Облачно - от серого к белому

# Добавить класс DatabaseUpdater с методами:
#   Получающим данные из базы данных за указанный диапазон дат.
#   Сохраняющим прогнозы в базу данных (использовать peewee)

# Сделать программу с консольным интерфейсом, постаравшись все выполняемые действия вынести в отдельные функции.
# Среди действий, доступных пользователю, должны быть:
#   Добавление прогнозов за диапазон дат в базу данных
#   Получение прогнозов за диапазон дат из базы
#   Создание открыток из полученных прогнозов
#   Выведение полученных прогнозов на консоль
# При старте консольная утилита должна загружать прогнозы за прошедшую неделю.

# Рекомендации:
# Можно создать отдельный модуль для инициализирования базы данных.
# Как далее использовать эту базу данных в движке:
# Передавать DatabaseUpdater url-путь
# https://peewee.readthedocs.io/en/latest/peewee/playhouse.html#db-url
# Приконнектится по полученному url-пути к базе данных
# Инициализировать её через DatabaseProxy()
# https://peewee.readthedocs.io/en/latest/peewee/database.html#dynamically-defining-a-database

# -*- coding: utf-8 -*-

import datetime
import re
import exceptions_metcast
import argparse

from weather_engine import WeatherMaker, DatabaseUpdater, ImageMaker
from abc import ABC, abstractmethod


class WeatherInterface(ABC):
    """Шаблон интерфейса"""

    def __init__(self):
        self.weather_maker = WeatherMaker()
        self.db_updater = DatabaseUpdater()
        self.image_maker = ImageMaker()
        self.current_metcast_info = None
        self.user_choice = {
            "1": {
                "text": "Введите название города или локации:",
                "func": self.change_city
            },
            "2": {
                "text": "Введите диапазон дат или дату:",
                "func": self.parse_and_save
            },
            "3": {
                "text": "Введите диапазон дат или дату:",
                "func": self.get_info
            },
            "4": {"func": self.draw_postcard},
            "5": {"func": self.print_metcast_to_console}
        }

    def menu_to_console(self):
        """Вывод меню на консоль меню"""
        print("\n1. Ввести название города;")
        print("2. Добавление прогнозов за диапазон дат в базу данных;")
        print("3. Получение прогнозов за диапазон дат из базы;")
        print("4. Создание открыток из полученных прогнозов;")
        print("5. Выведение полученных прогнозов на консоль;")
        print("Формат ввода даты YYYY-MM-DD:YYYY-MM-DD (Выборка прогнозы погоды для установленного диапазона дат) "
              "или YYYY-MM-DD (Одно значение для данной даты).")

    def check_date(self, user_answer):
        """Проверка введенной даты"""
        compare = re.match(r"((\d{4}-\d{2}-\d{2}):(\d{4}-\d{2}-\d{2}))|(\d{4}-\d{2}-\d{2})", user_answer)
        if compare:
            if compare.group(1):
                start_date = compare.group(2)
                finish_date = compare.group(3)
                return True, start_date, finish_date
            else:
                start_date = compare.group(4)
                return True, start_date, None
        else:
            return False, None, None

    def change_city(self, user_answer):
        """Смена региона"""
        self.weather_maker.name_location = user_answer
        answer = f"\nИзменена область для прогноза погоды на {self.weather_maker.name_location}\n"
        return answer

    def init_first_info(self):
        """Получение прогноза погоды за прошлую неделю"""
        print("Можно выбрать город или локацию для вывода прогноза погоды. По умолчанию установлен город Москва.\n"
              "Операции запись (парсинг прогноза погоды) и чтнение из БД будет "
              "производится только для выбранного города (локации).\n"
              "Перед созданием открыток, убедитесь что в памяти есть "
              "данные о прогнозе погоды, для этого выберите пункт 5\n"
              "Парсинг прогноза погоды и запись в БД может быть только на 7 дней вперед от текузей даты "
              "(ограничение YandexAPI.Погода (Тестовый))")
        currnet_date = datetime.date.today()
        start_date = str(currnet_date - datetime.timedelta(days=7))
        finish_date = str(currnet_date - datetime.timedelta(days=1))
        self.current_metcast_info = self.db_updater.get_data(
            location_user=self.weather_maker.name_location,
            start_date=start_date,
            finish_date=finish_date
        )

    def get_info(self, user_answer):
        """Получение прогноза погоды из базы"""
        compare, start_date, finish_date = self.check_date(user_answer)
        if compare:
            self.current_metcast_info = self.db_updater.get_data(
                location_user=self.weather_maker.name_location,
                start_date=start_date,
                finish_date=finish_date
            )
            if self.current_metcast_info:
                answer = "\nДанные загружены из базы удачно"
            else:
                answer = "\nДанные по введенным параметрам отсутствуют"
        else:
            answer = "Формат ввода даты YYYY-MM-DD:YYYY-MM-DD или YYYY-MM-DD."
        return answer

    def parse_and_save(self, user_answer):
        """Парсинг прогноза погоды и запись в БД"""
        compare, start_date, finish_date = self.check_date(user_answer)
        if compare:
            try:
                self.current_metcast_info = self.weather_maker.date_selection_data(
                    start_date_str=start_date,
                    finish_date_str=finish_date
                )
                if self.current_metcast_info:
                    answer = "\nДанные загружены в базы удачно"
                else:
                    answer = "\nДанные по введенным параметрам отсутствуют"
            except exceptions_metcast.YandexGeoLocationError:
                answer = "\nНе удалось определить локацию."
        else:
            answer = "Формат ввода даты YYYY-MM-DD:YYYY-MM-DD или YYYY-MM-DD."
        return answer

    def draw_postcard(self):
        if self.current_metcast_info:
            self.image_maker.draw_postcard(self.current_metcast_info)
            answer = "Открытки сформированы."
        else:
            answer = "К сожалению данные о прогнозе погоды для данного диапазона дат или локации отсутствуют."
        return answer

    def print_metcast_to_console(self):
        """Вывод прогноза погоды на консоль"""
        metcast_string = list()
        if self.current_metcast_info:
            for day in self.current_metcast_info:
                string_day = f"{day['location']['name_location']}, дата {str(day['date'])}, " \
                             f"погодные условия {day['condition']}, температура {day['temp']} С, " \
                             f"влажность {day['humidity']}, давление {day['pressure_mm']} мм рт. ст.;"
                metcast_string.append(string_day)
            answer = "\n".join(metcast_string)
        else:
            answer = "К сожалению данные о прогнозе погоды для данного диапазона дат или локации отсутствуют."
        return answer

    def processing_choice(self, number):
        """Обработка пользовательского ввода"""
        compare = re.fullmatch(r"[1-5]", number)
        if compare:
            if "text" in self.user_choice[number]:
                user_answer = input(self.user_choice[number]["text"])
                answer = self.user_choice[number]["func"](user_answer)
            else:
                answer = self.user_choice[number]["func"]()
            print(answer)
        else:
            print("\nНеобходимо ввести номер пункта 1-5\n")

    @abstractmethod
    def main(self):
        pass


class WeatherInterfaceModule(WeatherInterface):
    """Реализация для модуля"""

    def main(self):
        """Основной цикл программы"""
        self.init_first_info()
        while True:
            self.menu_to_console()
            user_input = input("\nВведиде номер пункта:")
            self.processing_choice(number=user_input)


class WeatherInterfaceArgParse(WeatherInterface):
    """Реализация для терминала"""

    def __init__(self, args):
        super().__init__()
        self.args = args

    def main(self):
        """Основной цикл программы"""
        if self.args.location:
            print(self.change_city(self.args.location))
        if self.args.mode == "parse_write":
            print(self.parse_and_save(self.args.date))
        else:
            print(self.get_info(self.args.date))
        if self.args.writing == "console":
            print(self.print_metcast_to_console())
        else:
            print(self.draw_postcard())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Using the program, you can get and write to the database, "
                    "read from the database, display it on the console or print a postcard "
                    "of the weather forecast for a certain time range"
    )
    parser.add_argument("--loc", dest="location", help="Weather forecast location")
    parser.add_argument(
        "--d",
        dest="date",
        required=True,
        help="Date range (YYYY-MM-DD:YYYY-MM-DD) or date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--m",
        dest="mode",
        required=True,
        choices=["parse_write", "read"],
        help="Parsing and writing to the database or reading from database"
    )
    parser.add_argument(
        "--w",
        dest="writing",
        required=True,
        choices=["console", "postcard"],
        help="Display weather forecast on the console or print in postcard format"
    )
    try:
        args = parser.parse_args()
        weather = WeatherInterfaceArgParse(args)
    except Exception:
        weather = WeatherInterfaceModule()

    weather.main()

# зачет!
