# Generated by Django 3.2.7 on 2021-10-07 13:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crawler', '0012_auto_20211007_0748'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='article',
            unique_together={('title', 'keywords')},
        ),
    ]
