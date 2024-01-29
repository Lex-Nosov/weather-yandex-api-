# -*- coding: utf-8 -*-
import os

API_KEY_METCAST = "8ffa4276-112a-4253-8338-e6219b546e1d"

PARAMS_METCAST = {
    "lat": None,
    "lon": None,
    "limit": "7",
    "hours": "false",
    "format": "json",
    "lang": "ru_RU"
}

HEADER_METCAST = {
    "X-Yandex-API-Key": API_KEY_METCAST
}

CONDITION_SET = {
    ("clear",): "Солнечно",
    ("partly-cloudy", "cloudy", "overcast",): "Облачно",
    ("drizzle", "light-rain", "rain",
     "moderate-rain", "heavy-rain",
     "continuous-heavy-rain", "showers",
     "thunderstorm", "thunderstorm-with-rain",
     "thunderstorm-with-hail"): "Дождь",
    ("wet-snow", "light-snow", "snow",
     "snow-showers", "hail"): "Снег"
}

COLOR_SET = {
    "Солнечно": {
        "color1": (0, 255, 255),
        "color2": (255, 255, 255)
    },
    "Дождь": {
        "color1": (255, 0, 0),
        "color2": (255, 255, 255)
    },
    "Снег": {
        "color1": (255, 205, 0),
        "color2": (255, 255, 255)
    },
    "Облачно": {
        "color1": (100, 100, 100),
        "color2": (255, 255, 255)
    },
}

IMAGE_SET = {
    "Солнечно": os.path.join("weather_source_img", "sun.png"),
    "Дождь": os.path.join("weather_source_img", "rain.png"),
    "Снег": os.path.join("weather_source_img", "snow.png"),
    "Облачно": os.path.join("weather_source_img", "cloud.png")
}
