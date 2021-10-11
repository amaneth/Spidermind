#!/usr/bin/env python3

import os
import sys
import string
import logging
import logging.handlers as loghandlers
import configparser as cp
import threading
import datetime
import json

import newspaper as nwp
import feedparser as fp
from newspaper import Article as NPA

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
loghandle = loghandlers.TimedRotatingFileHandler(
                filename="SNETnews.log",
                when='D', interval=1, backupCount=7,
                encoding="utf-8")
loghandle.setFormatter(
    logging.Formatter("%(asctime)s %(message)s"))
logger.addHandler(loghandle)

NLP_MODE = 1
NO_NLP_MODE = 0
RSS_ONLY_MODE = 2
RSS_WITH_NLP_MODE = 3 


class SNETnews:
    def __init__(self, conf_file='./news.ini'):
        logger.info("Initializing SNETnews. Conf file: " + conf_file)
        config_f = cp.ConfigParser()
        config_f.read(conf_file)
        self.papers = []
        self.number_of_sites=0
        self.source_sites = []
        self.rss_sites= ['http://rss.cnn.com/rss/cnn_topstories.rss']
        self.search_index = {}
        self.articles = []
        self.rss_articles =[]
        self.article_tags = {}
        self.article_sources = {}
        self.op_mode = 2 # 0 -> download & nlp + 1, 1 -> title + summary + tags
        self.refresh_rate = 0
        self.auto_refresh_timer = None
        self.continue_auto_refresh = True
        self.n_config = nwp.Config()
        self.min_html_chars = 0

        if config_f.sections().count('Article') == 1:
            article_c = config_f['Article']
            self.n_config.MIN_WORD_COUNT = int(article_c.get("min_word_count", 300))
            self.n_config.MIN_SENT_COUNT = int(article_c.get("min_sentence_count", 7))
            self.min_html_chars = int(article_c.get("min_html", 3000))
            self.n_config.MAX_TITLE = int(article_c.get("max_title", 200))
            self.n_config.MAX_TEXT = int(article_c.get("max_text", 100000))
            self.n_config.MAX_KEYWORDS = int(article_c.get("max_keywords", 35))
            self.n_config.MAX_AUTHORS = int(article_c.get("max_authors", 10))
            self.n_config.MAX_SUMMARY = int(article_c.get("max_summary", 5000))
            self.n_config.MAX_SUMMARY_SENT = int(article_c.get("max_summary_sentence", 5))
            #self.n_config.memoize_articles=False
            logger.info("Done with configuration for Article section MIN word cout: "+ \
                    str(self.n_config.MIN_WORD_COUNT))
        else:
            print("Warning: Couldn't find 'Article' section in config file")
            logger.warning("Warning: Couldn't find 'Article' section in config file")

        if config_f.sections().count('Sources') == 1:
            source_c = config_f['Sources']
            self.n_config.MAX_FILE_MEMO = int(source_c.get("max_cache_item", 20000))
            self.n_config.memoize_articles = source_c.getboolean("cache_articles")
            self.n_config.fetch_images = source_c.getboolean("fetch_images")
            self.n_config.image_dimension_ration = \
                        (float(source_c.get("image_dimension_width", 16)) / \
                        float(source_c.get("image_dimension_height", 9)))
            self.n_config.follow_meta_refresh = \
                        source_c.getboolean("follow_meta_refresh")
            self.n_config.keep_article_html = \
                        source_c.getboolean("keep_article_html")
            self.n_config._language = source_c.get("default_language", 'en')
            self.n_config.browser_user_agent = \
                        source_c.get("crawler_user_agent", "singnetnews/srv")
            self.n_config.number_threads = \
                        int(source_c.get("number_of_threads", 1))
            logger.info("Done with configuration for Sources setion: Memoize artices :"+ \
                    str(self.n_config.memoize_articles))
        else:
            print("Warning: Couldn't find 'Source' secion in config file")
            logger.warning("Warning: Couldn't find 'Source' section in config file")

        if config_f.sections().count('Misc') == 1:
            misc_c = config_f['Misc']
            self.op_mode = int(misc_c.get("op_mode", 0))
            self.refresh_rate = int(misc_c.get("refresh_rate", 300))
            logger.info("Done with configuration for MISC: OP MODE " + str(self.op_mode))
        if config_f.sections().count('NumberOfSites') == 1:
            site_n = config_f['NumberOfSites']
            self.number_of_sites = int(site_n.get("sites", 10))
            self.source_sites= ['http://www.bbc.co.uk']
            logger.info(" Done with configuration for number of sites: " + str(self.number_of_sites))
        if config_f.sections().count('RSSFeedList') == 1:
            rss_l = config_f['RSSFeedList']
            #self.rss_sites = rss.get("rss").replace(" ","").replace("\n", "").split(",")
            self.rss_sites = ['http://feeds.bbci.co.uk/news/world/rss.xml']
            logger.info(" Done with configuration for RSS feed list: " + str(len(self.rss_sites)))


       # if config_f.sections().count('SiteList') == 1:
       #     site_l = config_f['SiteList']
       #     self.source_sites = \
       #         site_l.get("sites").replace(" ","").replace("\n","").split(",")
        
        logger.info("Done Initialization")

    # TO DO while web crawling I highly recommend using proxy services as well
    # since it will be useful in many various ways.
    # The main reason to use such services is to avoid being detected from the website 
    # and being banned since web crawling is automatic action and might raise suspicions
    # (since most of the web pages doesn’t want you to crawl their data). meanwhile,
    # when using proxies you have a big pool of IPs that are constantly changing
    # so your actions looks more like real human activity,
    # thus you can way easier web crawl web page.
    # TO DO drop articles other than english language or mange them
    def download_news(self):
        op_map = {0: 'NO_NLP', 1: 'NLP', 2: 'RSS_ONLY', 3:'RSS_WITH_NLP'}
        logger.info("Retrieving news from sites. {} Mode: ".format(op_map[self.op_mode]))
        logger.info("Memoize articles is sat " + str(self.n_config.memoize_articles))
        if((self.op_mode == NLP_MODE) or (self.op_mode ==NO_NLP_MODE) ):
            self.papers = [nwp.build(site, config=self.n_config) for site in self.source_sites]
            logger.info("NLP & NO NLP: Crawler is done with building source  Papers:"\
                    + str(len(self.papers)))
            if((self.op_mode == NLP_MODE)):
                #nwp.news_pool.set(self.papers, threads_per_source=2)
                #nwp.news_pool.join() # download articles in a pool multithreadedly is \
                        # good practice but here there are also articles not filtered, downloading \
                        # them too is costly.
                logger.info("NLP: Done Downloading News.NLP: No Articles: " \
                    + str(len(sum([n.articles for n in self.papers], []))))
                self.articles = [a for a in sum([n.articles for n in self.papers],
                                            []) if a.title != None] \
                    # check all the fields if they exist may be better
                logger.info("NLP: Done Filtering. No Articles: " + str(len(self.articles)))
                count = 0
                for article in self.articles:
                    try:
                        article.download()
                        article.parse()
                        article.nlp()
                    except:
                        count+=1
                        continue # passing some bad urls, but fixing can save them
                logger.info("RSS NLP: {} articles with bad url has jumped".format(count))
                self.articles = [ a.__dict__ for a in self.articles] \
                        # change it to dictionary to add source type tag
                logger.info("NLP: Done with building a dict, NLP: keyword example: "+ \
                        str(self.articles[0].get('keywords',"Nothing found"))
                        if len(self.articles)>0 else\
                        "no articles has crawled" )
                for article in self.articles:
                    article['source_type'] = 'crawl_nlp'
                logger.info("NLP: Done with inserting tag NO NLP: example: "+ \
                        str(self.articles[0].get('source_type',"no source type found"))
                        if len(self.rss_articles)>0 else\
                        "no rss has downloaded")
            else:
                self.articles = \
                    [a for a in sum([n.articles for n in self.papers], self.articles) \
                        if a.title != None]
                logger.info("NO NLP: Done Filtering NONLP. No Articles: " \
                            + str(len(self.articles)))
                self.articles = [ a.__dict__ for a in self.articles]
                for article in self.articles:
                    article['source_type'] = 'crawl'
                logger.info("NO NLP: Done with inserting tag NLP: example: "+ \
                        str(self.articles[0].get('source_type',"no source type found")))
        #TO DO memoize articles rss
        elif (self.op_mode == RSS_ONLY_MODE):
            self.papers= [ fp.parse(site) for site in self.rss_sites]
            self.articles = [x for y in [n.entries for n in self.papers] for x in y] \
                    # filtering is good to be here
            logger.info("RSS: Done parsing news, No Articles" + str(len(self.rss_articles)))
            for article in self.articles:
                article['source_type']='rss'
            logger.info("RSS: Done building a source tag rss, example {}".format(
                str(self.articles[0].get('source_type',"no rss source type found")) \
                        if len(self.articles)>0 else\
                        "no rss has downloaded"))
        else:
            #TO DO do rss_crawl with nlp_crawl just changing the site source
            #TO DO only the content from newspaper, feedparser better on the rest
            self.papers= [ fp.parse(site) for site in self.rss_sites]
            self.articles = [x for y in [n.entries for n in self.papers] for x in y] \
                    # filtering is good to be here
            logger.info("RSS NLP: Done parsing news, No Articles" + str(len(self.articles)))
            count = 0
            articles_temp=[]
            for article in self.articles:
                article = NPA(article.link)
                try:
                    article.download()
                    article.parse()
                    article.nlp()
                    articles_temp.append(article)
                    #TO DO download articels in news_pool
                except:
                    count+=1
                    pass
            self.articles = articles_temp
            logger.info("RSS NLP: {} articles with bad url has jumped".format(count))
            self.articles = [ a.__dict__ for a in self.articles] \
                        # change it to dictionary to add source type tag
            logger.info("RSS NLP: Done with building a dict, NLP: keyword example: "+ \
                str(self.articles[0].get('keywords',"Nothing found"))
                    if len(self.articles)>0 else\
                    "no articles has crawled" )
            for article in self.articles:
                article['source_type'] = 'rss_nlp'
            logger.info("RSS NLP: Done with inserting tag NO NLP: example: "+ \
                    str(self.articles[0].get('source_type',"no source type found"))
                    if len(self.articles)>0 else\
                    "no rss has downloaded")
        logger.info("Done retrieving news from sites")
        #logger.info("Search Index Built: " + str(sys.getsizeof(self.search_index)))
        return self.articles
    def auto_refresh(self):
        #TO DO build api for refresh
        logger.info("AutoRefresh: " + str(self.continue_auto_refresh))
        if self.continue_auto_refresh:
            self.download_news();
            self.auto_refresh_timer = threading.Timer(self.refresh_rate,
                                                      self.auto_refresh)
            self.auto_refresh_timer.start()

    def start_auto_refresh(self):
        logger.info("Start Autorefresh")
        self.auto_refresh_timer = threading.Timer(self.refresh_rate,
                                                  self.auto_refresh)
        self.auto_refresh_timer.start()
        self.continue_auto_refresh = True

    def stop_auto_refresh(self):
        logger.info("Stop Autorefresh")
        if self.auto_refresh_timer == None:
            raise Exception("No Event Loop Timer Registered")
        self.auto_refresh_timer.cancel()
        self.continue_auto_refresh = False
