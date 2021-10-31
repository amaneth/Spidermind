import time
from newspaper_crawler.celery import app
from crawler.utils.news import SNETnews
from celery.utils.log import get_task_logger
from celery import shared_task
from django.core.cache import cache
from django.core.cache import caches
from hashlib import md5
from crawler.views import snet


logger = get_task_logger(__name__)

LOCK_EXPIRE = 60 * 10  # Lock expires in 10 minutes

@shared_task
def download():
    op_mode = snet.op_mode
    op_map = {0: 'NO_NLP', 1: 'NLP', 2: 'RSS_ONLY', 3:'RSS_WITH_NLP'}
    #operation_mode_hexdigest = md5(str(op_mode).encode()).hexdigest()
    logger.debug('Importing feed in: %s', op_mode)
    acquired = cache.add(op_map[op_mode],"news",LOCK_EXPIRE)
    logger.debug("C---A---C---H--ED:"+str(acquired))
    if acquired:
        snet.download_news()
    else:
        logger.debug('Feed in  %s is already being imported by another worker', op_mode)
