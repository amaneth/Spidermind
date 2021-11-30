from django.db import models

# Create your models here.
class Article(models.Model):
    content_id = models.CharField(max_length=60, default='')
    title = models.CharField(unique=True, max_length=200, blank=True, default='')
    description = models.TextField()
    authors = models.CharField(max_length=40, blank=True, default='')
    date = models.DateTimeField(auto_now_add = True)
    link = models.CharField(max_length=400, blank=True, default='')
    top_image = models.CharField(max_length=400, blank=True, default='')
    keywords= models.CharField(max_length=400, blank=True, default='')
    source_type = models.CharField(max_length=100)
    source = models.CharField(max_length=100, default='unknown')
    


