from django.db import models

# Create your models here.
class Article(models.Model):
    title = models.CharField(max_length=200, blank=True, default='')
    description = models.TextField()
    authors = models.CharField(max_length=40, blank=True, default='')
    date = models.CharField(max_length=20, blank=True, default='')
    link = models.CharField(max_length=400, blank=True, default='')
    source_type = models.CharField(max_length=100)

