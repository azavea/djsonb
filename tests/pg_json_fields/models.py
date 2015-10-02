# -*- coding: utf-8 -*-

from django.db import models
from django_pgjson.fields import JsonBField


class JsonBModel(models.Model):
    data = JsonBField()
