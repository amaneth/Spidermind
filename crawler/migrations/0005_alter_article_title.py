# Generated by Django 3.2.7 on 2021-09-16 14:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crawler', '0004_article_keywords'),
    ]

    operations = [
        migrations.AlterField(
            model_name='article',
            name='title',
            field=models.CharField(blank=True, default='', max_length=200, unique=True),
        ),
    ]