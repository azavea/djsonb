# -*- coding: utf-8 -*-

from django.db import models
from djsonb.fields import JsonBField


class JsonBModel(models.Model):
    data = JsonBField()
