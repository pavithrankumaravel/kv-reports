from django.db import models

# Create your models here.

from django.db import models

class DefaultModel(models.Model):  # Uses 'default' DB
    title = models.CharField(max_length=100)

class DB2Model(models.Model):  # We want this in db2
    name = models.CharField(max_length=100)

class DB3Model(models.Model):  # We want this in db3
    value = models.IntegerField()
