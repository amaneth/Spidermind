import time
from newspaper_crawler.celery import app
from crawler.utils.news import SNETnews
from celery.utils.log import get_task_logger
from contextlib import contextmanager
from django.core.cache import cache 
from hashlib import md5
from crawler.views import snet


logger = get_task_logger(__name__)

LOCK_EXPIRE = 60 * 10  # Lock expires in 10 minutes


@contextmanager
def memcache_lock(lock_id, oid):
    timeout_at = time.monotonic() + LOCK_EXPIRE - 3
    # cache.add fails if the key already exists
    logger.debug(str([lock_id, oid, LOCK_EXPIRE]))
    status = cache.add(lock_id, oid, LOCK_EXPIRE)
    try:
        yield status
    finally:
        # memcache delete is very slow, but we have to use it to take
        # advantage of using add() for atomic locking
        if time.monotonic() < timeout_at and status:
            # don't release the lock if we exceeded the timeout
            # to lessen the chance of releasing an expired lock
            # owned by someone else
            # also don't release the lock if we didn't acquire it
            cache.delete(lock_id)

@app.task(bind=True)
def download(self):
    op_mode = snet.op_mode
    operation_mode_hexdigest = md5(str(op_mode).encode()).hexdigest()
    lock_id = '{0}-lock-{1}'.format(self.name, operation_mode_hexdigest)
    logger.debug('Importing feed in: %s', op_mode)
    with memcache_lock(lock_id, "Hello") as acquired:
        logger.debug("acquired"+str(acquired))
        if acquired:
            snet.download_news()
            logger.debug("done here"+lock_id+ "app"+ self.app.oid)
        else:
            logger.debug('Feed in  %s is already being imported by another worker', op_mode)
