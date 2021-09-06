from django.db import models

# Create your models here.
class Article(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    authors = models.CharField(max_length=40)
    date = models.CharField(max_length=20)
    link = models.CharField(max_length=400)
    search_terms= models.CharField(max_length=100)
