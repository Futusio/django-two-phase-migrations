import logging

import pytz
from django.conf import settings
from django.db import models

my_tz = pytz.timezone(settings.TIME_ZONE)
logger = logging.getLogger(__name__)

from django.db import models


class Order(models.Model):
    # Раньше: number = models.CharField(max_length=32)
    number = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        pass

