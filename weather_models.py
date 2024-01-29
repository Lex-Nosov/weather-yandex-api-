# -*- coding: utf-8 -*-
import os
import peewee as pw

if not os.path.exists("database_metcast"):
    os.mkdir("database_metcast")
path_db = os.path.join("database_metcast", "metcast.db")

url_bd = f"sqlite:///{path_db}"
database_proxy = pw.DatabaseProxy()


class BaseTeble(pw.Model):
    class Meta:
        database = database_proxy


class Location(BaseTeble):
    name_location = pw.CharField()
    latitude = pw.FloatField()
    longitude = pw.FloatField()


class Metcast(BaseTeble):
    location = pw.ForeignKeyField(Location)
    date = pw.DateField()
    condition = pw.CharField()
    temp = pw.IntegerField()
    humidity = pw.IntegerField()
    pressure_mm = pw.IntegerField()
