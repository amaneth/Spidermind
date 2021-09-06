#!/usr/bin/env python3

from django.shortcuts import render

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

from crawler.models import Article

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
loghandle = loghandlers.TimedRotatingFileHandler(
                filename="SNETnews.log",
                when='D', interval=1, backupCount=7,
                encoding="utf-8")
loghandle.setFormatter(
    logging.Formatter("%(asctime)s %(message)s"))
logger.addHandler(loghandle)

NLP_MODE = 0
NONLP_MODE = 1
class SNETnews:
    def __init__(self, conf_file='../news.ini'):
        logger.info("Initializing SNETnews. Conf file: " + conf_file)
        config_f = cp.ConfigParser()
        config_f.read(conf_file)
        self.papers = []
        self.number_of_sites=0
        self.source_sites = []
        self.search_index = {}
        self.articles = []
        self.article_tags = {}
        self.article_sources = {}
        self.op_mode = 0 # 0 -> download & nlp + 1, 1 -> title + summary + tags
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
        else:
            print("Warning: Couldn't find 'Article' section in config file")
            logger.warning("Warning: Couldn't find 'Article' section in config file")

        if config_f.sections().count('Sources') == 1:
            source_c = config_f['Sources']
            self.n_config.MAX_FILE_MEMO = int(source_c.get("max_cache_item", 20000))
            self.n_config.memoize_articles = bool(source_c.get("cache_articles", True))
            self.n_config.fetch_images = bool(source_c.get("fetch_images", True))
            self.n_config.image_dimension_ration = \
                        (float(source_c.get("image_dimension_width", 16)) / \
                        float(source_c.get("image_dimension_height", 9)))
            self.n_config.follow_meta_refresh = \
                        bool(source_c.get("follow_meta_refresh", True))
            self.n_config.keep_article_html = \
                        bool(source_c.get("keep_article_html", False))
            self.n_config._language = source_c.get("default_language", 'en')
            self.n_config.browser_user_agent = \
                        source_c.get("crawler_user_agent", "singnetnews/srv")
            self.n_config.number_threads = \
                        int(source_c.get("number_of_threads", 1))
        else:
            print("Warning: Couldn't find 'Source' secion in config file")
            logger.warning("Warning: Couldn't find 'Source' section in config file")

        if config_f.sections().count('Misc') == 1:
            misc_c = config_f['Misc']
            self.op_mode = int(misc_c.get("op_mode", 0))
            self.refresh_rate = int(misc_c.get("refresh_rate", 300))
        if config_f.sections().count('NumberOfSites') == 1:
            site_n = config_f['NumberOfSites']
            self.number_of_sites = int(site_n.get("sites", 10))
            self.source_sites=nwp.popular_urls()[:self.number_of_sites]

       # if config_f.sections().count('SiteList') == 1:
       #     site_l = config_f['SiteList']
       #     self.source_sites = \
       #         site_l.get("sites").replace(" ","").replace("\n","").split(",")

        logger.info("Done Initialization")

    def download_news(self):
        logger.info("Retrieving news from sites. Op Mode: " \
                    + "NLP Mode" if self.op_mode == 0 else "NO NLP Mode")
        self.papers = [nwp.build(site, config=self.n_config) for site in self.source_sites]
        logger.info("   Papers:" + str(self.papers))
        if(self.op_mode == NLP_MODE):
            nwp.news_pool.set(self.papers, threads_per_source=2)
            nwp.news_pool.join()
            logger.info("Done Downloading News. No Articles: " \
                + str(len(sum([n.articles for n in self.papers], []))))
            self.articles = [a for a in sum([n.articles for n in self.papers],
                                            self.articles) \
                if a.title != None and len(a.html) > self.min_html_chars]
            logger.info("Done Filtering. No Articles: " + str(len(self.articles)))
            for article in self.articles:
                article.parse()
                article.nlp()
                self.search_index[article] = article.keywords \
                    + article.title.translate(
                        str.maketrans(
                            '', '', string.punctuation)).split(" ") \
                    + article.summary.translate(
                        str.maketrans(
                            '', '', string.punctuation)).split(" ")

        else:
            self.articles = \
                [a for a in sum([n.articles for n in self.papers], self.articles) \
                    if a.title != None]
            logger.info("Done Filtering NONLP. No Articles: " \
                        + str(len(self.articles)))
            for article in self.articles:
                if article.title != None and article.summary != None:
                    self.search_index[article] = \
                        article.title.translate(
                            str.maketrans(
                                '', '', string.punctuation)).split(" ") \
                        + article.summary.translate(
                            str.maketrans(
                                '', '', string.punctuation)).split(" ")

        logger.info("Done retrieving news from sites")
        logger.info("Search Index Built: " + str(sys.getsizeof(self.search_index)))


    def search_news(self, request, terms, top_results=1):
        if request.method == 'GET':
            logger.info("Starting Search for " + str(len(terms)) + " and top results: " + str(top_results))
            search_rank = {}
            if isinstance(terms,str):
                terms=[terms]
            for article,keywords in self.search_index.items():
                for term in terms:
                    rank = 0
                    st = term.translate(
                        str.maketrans('', '', string.punctuation)).split(" ")
                    for t in st:
                        rank += keywords.count(t)
                    search_rank[article] = rank
            logger.info("Done Searching. Full Result: " + str(search_rank))
            _sel_articles = sorted(search_rank.items(),
                      key=lambda x : x[1],
                      reverse=True)[:min(len(search_rank), top_results)]
            if all(list(map(lambda x : x[1] == 0, _sel_articles))):
                return "Nothing Found"
        return HttpResponse(self.encode_json(dict(_sel_articles).keys()))

    def get_news(self, request, sort_type="title", results=10):
        if request.method == 'GET':
            logger.info("Get News - Sort Type: " \
                        + str(sort_type) \
                        + " - Results: " \
                        + str(results))
            if sort_type == "title":
                logger.info("Sort Type: title, No Articles: " + str(len(self.articles)))
                return self.encode_json(
                    sorted(self.articles,
                           key=lambda x : x.title)[:min(results, len(self.articles))])
            elif sort_type == "date":
                return HttpResponse(self.encode_json(sorted(self.articles, \
                              key=lambda x : x.publish_date.timestamp() \
                                             if isinstance(x.publish_date, datetime.datetime) \
                                                and type(x.publish_date) != 'str' \
                                             else 0.0, \
                              reverse=True)[:min(results, len(self.articles))]))

    def trending_topics(self, request):
        if request.method == 'GET':
            topics=nwp.hot()
            logger.info("retrieving "+ str(len(topics)) +" trending topics")
            return self.search_news(topics,5)

    def encode_json(self, articles):
        logger.info("Encoding to JSON: " + str(len(articles)) + " articles")
        j = []
        for article in articles:
            j.append({
                "title" : article.title,
                "description" : article.summary,
                "authors" : article.authors,
                "date" : str(article.publish_date),
                "link" : article.url})
        return json.dumps(j)

    def auto_refresh(self):
        logger.info("AutoRefresh: " + str(self.continue_auto_refresh))
        if self.continue_auto_refresh:
            self.download_news();
            self.auto_refresh_timer = threading.Timer(self.refresh_rate,
                                                      self.auto_refresh)
            self.auto_refresh_timer.start()


    def start_auto_refresh(self, request):
        if request.method == 'GET':
            logger.info("Start Autorefresh")
            self.auto_refresh_timer = threading.Timer(self.refresh_rate,
                                                  self.auto_refresh)
            self.auto_refresh_timer.start()
            self.continue_auto_refresh = True

    def stop_auto_refresh(self, request):
        if request.method == 'GET':
            logger.info("Stop Autorefresh")
            if self.auto_refresh_timer == None:
                raise Exception("No Event Loop Timer Registered")
            self.auto_refresh_timer.cancel()
            self.continue_auto_refresh = False

