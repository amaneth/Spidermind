from django.apps import AppConfig
from django.db.models.signals import post_migrate

DEFAULT_RELEARN_TIME=10
def create_periodic_task(sender, **kwargs):
    from django_celery_beat.models import PeriodicTask, IntervalSchedule
    schedule, created = IntervalSchedule.objects.get_or_create(every=DEFAULT_RELEARN_TIME,
                period=IntervalSchedule.SECONDS,
                )
    PeriodicTask.objects.update_or_create(
                name='refreshing the database',
                defaults={'task':'crawler.tasks.download', 'interval':schedule},
                )

def create_categories(sender, **kwargs):
    from crawler.models import Setting
    Setting.objects.update_or_create(section_name='category', setting_name='ai', setting_type=2,
            defaults={'setting_value':"AI artificial intelligence robotics robot natural-language-processing\
                 nlp machine-learning GAI  intelligen"})

    Setting.objects.update_or_create(section_name='category', setting_name='blockchain', setting_type=2,
            defaults={'setting_value':"cryptographic blockchain token ethereum bitcoin\
                                crypto crypto-cash crypto-currency online-transactions cyber-cash"})

    Setting.objects.update_or_create(section_name='category', setting_name='computer', setting_type=2,
            defaults={'setting_value':"pc computer laptop desktop netbook mobile tablet multiprocessor microprocessor \
                           microcomputer mainframe supercomputer automation telecommunications electronics"})

    Setting.objects.update_or_create(section_name='category', setting_name='programming', setting_type=2,
            defaults={'setting_value':"Ahack coding software application programming natural-language-processing machine-learning\
                              software java python ruby mysql php laravel robotics JavaScript C# arduino"})
    


class CrawlerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crawler'
    verbose_name = "newspaper crawler"
    def ready(self):
        post_migrate.connect(create_periodic_task, sender=self)
        post_migrate.connect(create_categories, sender=self)
