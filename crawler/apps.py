from django.apps import AppConfig
from django.db.models.signals import post_migrate


def create_periodic_task(sender, **kwargs):
    from django_celery_beat.models import PeriodicTask, IntervalSchedule
    schedule, created = IntervalSchedule.objects.get_or_create(every=10,
                period=IntervalSchedule.SECONDS,
                )
    PeriodicTask.objects.update_or_create(
                name='refreshing the database',
                defaults={'task':'crawler.tasks.download', 'interval':schedule},
                )

def create_categories(sender, **kwargs):
    from crawler.models import Setting
    Setting.objects.update_or_create(section_name='category', setting_name='ai', setting_type=2,
            defaults={'setting_value':"'AI artificial intelligence robotics robote natural-language-processing nlp machine-learning machine learning natural language processing  knowledge intelligent'"})

class CrawlerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crawler'
    verbose_name = "newspaper crawler"
    def ready(self):
        post_migrate.connect(create_periodic_task, sender=self)
        post_migrate.connect(create_categories, sender=delf)
