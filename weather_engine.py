# -*- coding: utf-8 -*-
import os
import cv2
import requests
import datetime

import settings_metcast as set_met
import exceptions_metcast as exc_met
import weather_models as db_init

from weather_models import Metcast, Location
from playhouse.db_url import connect
from copy import deepcopy

AVAILABLE_CITIES = {'Moscow': {'lat': '55.754557', 'lon': '38.048162'},
                    'Saint Petersburg': {'lat': '59.9', 'lon': '30.4'}}


class WeatherMaker:
    """Парсинг координат и прогноза погоды"""

    def __init__(self, name_location="Moscow"):
        self.name_location = name_location
        self.week_metcast = list()
        self.db_metcast = DatabaseUpdater()

    def get_metcast(self):
        """
        Получение подробного прогноза погоды на 7 дней вперед.
        """
        coincidence, longitude, latitude = self.db_metcast.get_location_base(current_location=self.name_location)
        if not coincidence:
            latitude, longitude = AVAILABLE_CITIES[self.name_location]['lat'], AVAILABLE_CITIES[self.name_location][
                'lat']
        params = deepcopy(set_met.PARAMS_METCAST)
        params["lat"] = latitude
        params["lon"] = longitude
        response = requests.get(
            "https://api.weather.yandex.ru/v2/forecast?",
            params=params,
            headers=set_met.HEADER_METCAST
        )
        if response.status_code == 200:
            data = response.json()
            self.week_metcast.clear()
            for day in data["forecasts"]:
                metcast_day_info = dict(
                    location=dict(
                        name_location=self.name_location,
                        longitude=longitude,
                        latitude=latitude
                    ),
                    date=datetime.datetime.strptime(day["date"], "%Y-%m-%d").date(),
                    condition=day["parts"]["day"]["condition"],
                    temp=day["parts"]["day"]["temp_avg"],
                    humidity=day["parts"]["day"]["humidity"],
                    pressure_mm=day["parts"]["day"]["pressure_mm"]
                )
                self.week_metcast.append(metcast_day_info)
        else:
            raise exc_met.YandexMetCastResponseError("When requesting a metcast, the response is not 200")

    def date_selection_data(self, start_date_str, finish_date_str=None):
        """Выборка прогноза по дате в зависимости от ввода пользователя"""
        self.get_metcast()
        current_metcast_info = list()
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        for day in self.week_metcast:
            if finish_date_str:
                finish_date = datetime.datetime.strptime(finish_date_str, "%Y-%m-%d").date()
                if start_date <= day['date'] <= finish_date:
                    current_metcast_info.append(day)
            else:
                if start_date == day['date']:
                    current_metcast_info.append(day)
        self.db_metcast.write_data(current_metcast_info)
        return current_metcast_info


class DatabaseUpdater:
    """Чтение и запись из БД"""

    def __init__(self, url_bd=None, bd_module=None):
        self.url_bd = url_bd if url_bd else db_init.url_bd
        self.bd_module = bd_module if bd_module else db_init.database_proxy
        self.bd_metcast = connect(self.url_bd)
        self.bd_module.initialize(self.bd_metcast)
        self.bd_metcast.create_tables([Metcast, Location])
        self.bd_metcast.close()

    def get_location_base(self, current_location):
        """Получение из базы координат локации в случае, если она была"""
        for mc in Metcast.select():
            if mc.location.name_location == current_location:
                current_latitude = mc.location.latitude
                current_longitude = mc.location.longitude
                self.bd_metcast.close()
                return True, current_longitude, current_latitude
        else:
            self.bd_metcast.close()
            return False, None, None

    def append_result(self, mc, response, location_user):
        """Добавление запроса в итоговый результат"""
        if mc.location.name_location == location_user:
            result = dict(
                location=dict(
                    name_location=mc.location.name_location,
                    longitude=mc.location.longitude,
                    latitude=mc.location.latitude
                ),
                date=mc.date,
                condition=mc.condition,
                temp=mc.temp,
                humidity=mc.humidity,
                pressure_mm=mc.pressure_mm
            )
            response.append(result)
        return response

    def get_data(self, location_user, start_date, finish_date=None):
        """Чтение данных из БД"""
        response = list()
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        if finish_date:
            finish_date = datetime.datetime.strptime(finish_date, "%Y-%m-%d").date()
            for mc in Metcast.select().where(Metcast.date.between(start_date, finish_date)):
                response = self.append_result(mc, response, location_user)
        else:
            for mc in Metcast.select().where(Metcast.date == start_date):
                response = self.append_result(mc, response, location_user)
        self.bd_metcast.close()
        return response

    def write_data(self, current_metcast_info):
        """Запись в БД прогноза погоды"""
        metcast_info = deepcopy(current_metcast_info)
        loc = Location(
            name_location=metcast_info[0]["location"]["name_location"],
            latitude=metcast_info[0]["location"]["latitude"],
            longitude=metcast_info[0]["location"]["longitude"]
        )
        loc.save()
        for day in metcast_info:
            day["location"] = loc
        Metcast.replace_many(metcast_info).execute()
        self.bd_metcast.close()


class ImageMaker:
    """Создание открыток"""

    def __init__(self, path_name_postcards=None):
        self.path_name_postcards = path_name_postcards if path_name_postcards else "postcards"

    def color_background(self, condition, image, height, width):
        """Закрашивает фон"""
        color1 = set_met.COLOR_SET[condition]["color1"]
        color2 = set_met.COLOR_SET[condition]["color2"]
        bgr_list = [color1]
        for i in range(1, height):
            # Линейная интерполяция цвета, хвала гуглу
            curr_vector = tuple(int(color1[j] + (float(i) / (height - 1)) * (color2[j] - color1[j])) for j in range(3))
            bgr_list.append(curr_vector)
        for line in range(height):
            cv2.line(image, (0, line), (width, line), bgr_list[line], 1)
        return image

    def append_logo(self, condition, image):
        """Добавление иконки состояния погоды"""
        logo = cv2.imread(set_met.IMAGE_SET[condition])
        height_logo, width_logo, _ = logo.shape
        roi = image[10:height_logo + 10, 10:width_logo + 10]
        logo_gray = cv2.cvtColor(logo, cv2.COLOR_BGR2GRAY)
        ret, mask = cv2.threshold(logo_gray, 1, 255, cv2.THRESH_BINARY)
        mask_inv = cv2.bitwise_not(mask)
        image_bg = cv2.bitwise_and(roi, roi, mask=mask_inv)
        logo_fg = cv2.bitwise_and(logo, logo, mask=mask)
        dst = cv2.add(image_bg, logo_fg)
        image[10:height_logo + 10, 10:width_logo + 10] = dst
        return image

    def append_text(self, cond_ru, image, metcast_day, width):
        """Добавляем текст на открытку"""
        location = metcast_day["location"]["name_location"]
        date = metcast_day["date"].strftime("%d.%m.%Y")
        temp = f'Средняя температура: {metcast_day["temp"]} C град.'
        humidity = f'Влажность: {metcast_day["humidity"]} %'
        pressure = f'Давление: {metcast_day["pressure_mm"]} мм рт. ст.'
        cv2.putText(image, location, (int(width * .5), 30), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 0), 2)
        cv2.putText(image, date, (int(width * .5), 75), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 0), 2)
        cv2.putText(image, cond_ru, (int(width * .5), 120), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 0), 2)
        cv2.putText(image, temp, (10, 170), cv2.FONT_HERSHEY_COMPLEX, 0.75, (0, 0, 0), 2)
        cv2.putText(image, humidity, (10, 200), cv2.FONT_HERSHEY_COMPLEX, 0.75, (0, 0, 0), 2)
        cv2.putText(image, pressure, (10, 230), cv2.FONT_HERSHEY_COMPLEX, 0.75, (0, 0, 0), 2)
        return image, date

    def save_postcard(self, image, date):
        """Сохранение открытки"""
        if not os.path.exists(self.path_name_postcards):
            os.mkdir(self.path_name_postcards)
        postcard_name = os.path.join(self.path_name_postcards, f"postcard_{date}.jpg")
        cv2.imwrite(postcard_name, image)

    def draw_postcard(self, current_metcast_info):
        """Создание открытки с помощью OpenCV"""
        name_background = os.path.join("weather_source_img", "background.jpg")
        postcard_background = cv2.imread(name_background)
        height, width, _ = postcard_background.shape
        for metcast_day in current_metcast_info:
            image = postcard_background.copy()
            for key_cond, cond_ru in set_met.CONDITION_SET.items():
                if metcast_day["condition"] in key_cond:
                    break
            image = self.color_background(cond_ru, image, height, width)
            image = self.append_logo(cond_ru, image)
            image, date = self.append_text(cond_ru, image, metcast_day, width)
            self.save_postcard(image, date)
