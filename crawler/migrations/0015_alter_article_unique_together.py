# Generated by Django 3.2.7 on 2021-10-07 13:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crawler', '0014_alter_article_keywords'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='article',
            unique_together={('title', 'source_type')},
        ),
    ]
