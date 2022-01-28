from django.apps import AppConfig
from django.db.models.signals import post_migrate

REFRESH_RATE=10
# article_setting
MIN_WORD_COUNT = 300
MIN_SENTENCE_COUNT = 7
MIN_HTML = 3000
MAX_TITLE = 200
MAX_TEXT = 100000
MAX_KEYWORDS = 35
MAX_AUTHORS = 10
MAX_SUMMARY = 5000
MAX_SUMMARY_SENTENCE = 5

# Sources
MAX_CACHE_ITEM = 20000
CACHE_ARTICLES = False
FETCH_IMAGES = True
IMAGE_DIMENSION_WIDTH = 16
IMAGE_DIMENSION_HEIGHT = 9
FOLLOW_META_REFRESH  = False
KEEP_ARTICLE_HTML = False
DEFAULT_LANGUAGE = 'en'
CRAWLER_USER_AGENT = 'singnetnews/srv'
NUMBER_OF_THREADS = 10

# Misc
OPERATION_MODE = 3

#category
AI_RELATED_WORDS='ai artificial intelligence robotics robot natural-language-processing nlp machine-learning agi\
		intelligence alphago jhon mccarthy speech-recognition reinforcement-learning computer vision optimization\
	   artificial-general-intelligence character-recognition data-mining'
BLOCKCHAIN_RELATED_WORDS='crytography cryptographic block chain block-chain token ethereum bitcoin crypto\
		cryptocurrency wallet'

def create_periodic_task(sender, **kwargs):
    from django_celery_beat.models import PeriodicTask, IntervalSchedule
    schedule, created = IntervalSchedule.objects.get_or_create(every=REFRESH_RATE,
                period=IntervalSchedule.SECONDS,
                )
    PeriodicTask.objects.update_or_create(
                name='refreshing the database',
                defaults={'task':'crawler.tasks.download', 'interval':schedule},
                )

def create_default_configuration(sender, **kwargs):
	#Saves the default setting in the database.

    from crawler.models import Setting
    from crawler.utils.news import logger
    logger.info("Inserting the default configuration....")
	#category setting
    Setting.objects.update_or_create(section_name='category',
		   	setting_name='ai', 
			setting_type=2,
            defaults={'setting_value':AI_RELATED_WORDS})
    Setting.objects.update_or_create(section_name='category',
		   	setting_name='blockchain',
		   	setting_type=2,
            defaults={'setting_value':BLOCKCHAIN_RELATED_WORDS})

	#article
    Setting.objects.update_or_create(section_name='article',
		   	setting_name='min_word_count',
		   	setting_type=2,
            defaults={'setting_value':MIN_WORD_COUNT})
    Setting.objects.update_or_create(section_name='article', 
			setting_name='min_sentence_count', 
			setting_type=2,
            defaults={'setting_value':MIN_SENTENCE_COUNT})                            
    Setting.objects.update_or_create(section_name='article',
		   	setting_name='min_html',
		   	setting_type=2,
            defaults={'setting_value':MIN_HTML})
    Setting.objects.update_or_create(section_name='article', 
			setting_name='max_title',
		   	setting_type=2,
            defaults={'setting_value':MAX_TITLE})  
    Setting.objects.update_or_create(section_name='article',
		   	setting_name='max_text',
		   	setting_type=2,
            defaults={'setting_value':MAX_TEXT})
    Setting.objects.update_or_create(section_name='article',
		   	setting_name='max_keywords',
		   	setting_type=2,
            defaults={'setting_value': MAX_KEYWORDS})
    Setting.objects.update_or_create(section_name='article',
		   	setting_name='max_authors',
		   	setting_type=2,
            defaults={'setting_value':MAX_AUTHORS})
    Setting.objects.update_or_create(section_name='article',
		   	setting_name='max_summary',
		   	setting_type=2,
            defaults={'setting_value':MAX_SUMMARY})
    Setting.objects.update_or_create(section_name='article',
		   	setting_name='max_summary_sentence', 
			setting_type=2,
            defaults={'setting_value':MAX_SUMMARY_SENTENCE})
	
	#sources
    Setting.objects.update_or_create(section_name='source',
		   	setting_name='max_cache_item',
		   	setting_type=2,
            defaults={'setting_value':MAX_CACHE_ITEM})
    Setting.objects.update_or_create(section_name='source', 
			setting_name='cache_articles',
		   	setting_type=0,
            defaults={'setting_value':CACHE_ARTICLES})
    Setting.objects.update_or_create(section_name='source',
		   	setting_name='fetch_images',
		   	setting_type=0,
            defaults={'setting_value':FETCH_IMAGES})
    Setting.objects.update_or_create(section_name='source',
		   	setting_name='image_dimention_width',
		   	setting_type=2,
            defaults={'setting_value':IMAGE_DIMENSION_WIDTH})
    Setting.objects.update_or_create(section_name='source', 
			setting_name='image_dimention_height',
		   	setting_type=2,
            defaults={'setting_value':IMAGE_DIMENSION_HEIGHT})
    Setting.objects.update_or_create(section_name='source',
		   	setting_name='follow_meta_refresh', 
			setting_type=0,
            defaults={'setting_value':FOLLOW_META_REFRESH})
    Setting.objects.update_or_create(section_name='source',
		   	setting_name='keep_article_html',
		   	setting_type=0,
            defaults={'setting_value':KEEP_ARTICLE_HTML})
    Setting.objects.update_or_create(section_name='source',
		   	setting_name='default_language',
		   	setting_type=0,
            defaults={'setting_value':DEFAULT_LANGUAGE})
    Setting.objects.update_or_create(section_name='source',
		   	setting_name='crawler_user_agent',
		   	setting_type=0,
            defaults={'setting_value':CRAWLER_USER_AGENT})
    Setting.objects.update_or_create(section_name='source', 
			setting_name='number_of_threads',
		   	setting_type=2,
            defaults={'setting_value':NUMBER_OF_THREADS})     
	#sites
    Setting.objects.update_or_create(section_name='rss_source',
		   	setting_name='link', setting_type=2,
			defaults={'setting_value':'https://www.aitrends.com/feed/'})

	#misc
	# op_mode : operation mode of news retriever.
	#           1 -> nlp mode which downloads full article, performs text
	#                keyword extraction to add to search index (expensive)
	#           0 -> no nlp mode where the search index consists of article
	#                title, summary and tags.
	#           2 -> RSS only mode, The download is only RSS feed
	#           3 -> RSS with nlp mode, The download is RSS feed and nlp mode
    Setting.objects.update_or_create(section_name='misc', 
			setting_name='operation_mode',
		   	setting_type=3,
            defaults={'setting_value':OPERATION_MODE})
    Setting.objects.update_or_create(section_name='misc', 
			setting_name='refresh_rate', 
			setting_type=2,
            defaults={'setting_value':REFRESH_RATE}) 
    logger.info("Inserting the default configuration is done.")

class CrawlerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crawler'
    verbose_name = "newspaper crawler"
    def ready(self):
        post_migrate.connect(create_periodic_task, sender=self)
        post_migrate.connect(create_default_configuration, sender=self)
