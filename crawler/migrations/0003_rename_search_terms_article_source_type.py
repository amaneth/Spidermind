# Generated by Django 3.2.7 on 2021-09-15 08:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crawler', '0002_auto_20210912_1620'),
    ]

    operations = [
        migrations.RenameField(
            model_name='article',
            old_name='search_terms',
            new_name='source_type',
        ),
    ]
