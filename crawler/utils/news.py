#!/usr/bin/env python3

import os
import sys
import string
import logging
import logging.handlers as loghandlers
import configparser as cp
import threading
import datetime
import time
import json
from dateutil import parser
import re
import requests
import pickle

import newspaper as nwp
import feedparser as fp
from newspaper import Article as NewsPaperArticle
from nltk.corpus import stopwords
import uuid

from sklearn.feature_extraction.text import TfidfVectorizer
import nltk
from nltk.corpus import stopwords
from sklearn.metrics.pairwise import cosine_similarity

from crawler.models import Article, Setting
from crawler.serializers import ArticleSerializer
from django.db import IntegrityError
from django.core.cache import cache

import spacy

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
loghandle = loghandlers.TimedRotatingFileHandler(
                filename="SNETnews.log",
                when='D', interval=1, backupCount=7,
                encoding="utf-8")
loghandle.setFormatter(
    logging.Formatter("%(asctime)s %(message)s"))
logger.addHandler(loghandle)
spacy_nlp = spacy.load('en_core_web_sm')

NLP_MODE = 1
NO_NLP_MODE = 0
RSS_ONLY_MODE = 2
RSS_WITH_NLP_MODE = 3 

#RECOMMENDER_API = 'http://188.166.77.75:8020/articles'
RECOMMENDER_API = 'http://172.17.0.1:8020/articles'

class SNETnews:
    def __init__(self):
        logger.info("Initializing SNETnews... " )
        self.papers = []
        self.number_of_sites=0
        self.regular_source_sites = []
        self.rss_source_sites= ['http://rss.cnn.com/rss/cnn_topstories.rss']
        self.regular_links=[]
        self.search_index = {}
        self.articles = []
        self.article_tags = {}
        self.article_sources = {}
        self.op_mode = 2 # 0 -> download & nlp + 1, 1 -> title + summary + tags
        self.refresh_rate = 0
        self.auto_refresh_timer = None
        self.continue_auto_refresh = True
        self.n_config = nwp.Config()
        self.min_html_chars = 0
        self.op_map = {0: 'NO_NLP', 1: 'NLP', 2: 'RSS_ONLY', 3:'RSS_WITH_NLP'}


        if Setting.objects.filter(section_name='article').exists():
            self.n_config.MIN_WORD_COUNT = int(Setting.objects.get(section_name='article',
                    setting_name='min_word_count').setting_value)
            self.n_config.MIN_SENT_COUNT = int(Setting.objects.get(section_name='article',
                    setting_name='min_sentence_count').setting_value)
            self.html_chars = int(Setting.objects.get(section_name='article',
                    setting_name='min_html').setting_value)
            self.n_config.MAX_TITLE = int(Setting.objects.get(section_name='article',
                    setting_name='max_title').setting_value)
            self.n_config.MAX_TEXT = int(Setting.objects.get(section_name='article',
                    setting_name='max_text').setting_value)
            self.n_config.MAX_KEYWORDS = int(Setting.objects.get(section_name='article',
                    setting_name='max_keywords').setting_value)
            self.n_config.MAX_AUTHORS = int(Setting.objects.get(section_name='article',
                    setting_name='max_authors').setting_value)
            self.n_config.MAX_SUMMARY = int(Setting.objects.get(section_name='article',
                    setting_name='max_summary').setting_value)
            self.n_config.MAX_SUMMARY_SENT = int(Setting.objects.get(section_name='article',
                    setting_name='max_summary_sentence').setting_value)
            #self.n_config.memoize_articles=False
            logger.info("Done with configuration for Article section MIN word cout: "+ \
                    str(self.n_config.MIN_WORD_COUNT))
        else:
            print("Warning: Couldn't find 'Article' secion in the Setting database table")
            logger.warning("Warning: Couldn't find 'Article' section in the Setting database table")

        if Setting.objects.filter(section_name='source').exists():
            self.n_config.MAX_FILE_MEMO = int(Setting.objects.get(section_name='source',
                setting_name='max_cache_item').setting_value)
            self.n_config.memoize_articles = (Setting.objects.get(section_name='source',
                setting_name='cache_articles').setting_value)=='True'
            self.n_config.fetch_images = (Setting.objects.get(section_name='source',
                setting_name='fetch_images').setting_value) == 'True'

            self.n_config.image_dimension_ration =\
                    float(Setting.objects.get(section_name='source', setting_name='image_dimention_width')\
                    .setting_value)/\
                    float(Setting.objects.get(section_name='source', setting_name='image_dimention_height')\
                    .setting_value)
            self.n_config.follow_meta_refresh = \
                        Setting.objects.get(section_name='source', setting_name='follow_meta_refresh')\
                        .setting_value=='True'
            self.n_config.keep_article_html = \
                        Setting.objects.get(section_name='source', setting_name='keep_article_html')\
                        .setting_value=='True'
            self.n_config._language = Setting.objects.get(section_name='source', setting_name='default_language')\
                    .setting_value
            self.n_config.browser_user_agent = \
                        Setting.objects.get(section_name='source', setting_name='crawler_user_agent')\
                        .setting_value
            self.n_config.number_threads = \
                        int(Setting.objects.get(section_name='source', setting_name='number_of_threads')\
                        .setting_value)
            logger.info("Done with configuration for Sources setion: Memoize artices value: {} ".\
                    format(self.n_config.memoize_articles))
        else:
            print("Warning: Couldn't find 'Source' secion in config file")
            logger.warning("Warning: Couldn't find 'Source' section in config file")

        if Setting.objects.filter(section_name='misc').exists():
            self.op_mode = int(Setting.objects.get(section_name='misc', setting_name='operation_mode').\
                    setting_value)
            self.refresh_rate = int(Setting.objects.get(section_name='misc', setting_name='refresh_rate').\
                    setting_value)
            logger.info("Done with configuration for MISC: OPERATION MODE: {} ".format(self.op_mode))
        else:
            print("Warning: Couldn't find 'misc' section in the database Setting tabel")
            logger.warning("Warning: Couldn't find 'misc' section in the database Setting table")

        #We have three type of links links for rss feeds(rss_source), regular source links(regular_source) like
        # bbc.com and specific article links(link)
        if Setting.objects.filter(section_name='rss_source'):
            self.rss_source_sites = [e.setting_value for e in Setting.objects.filter(section_name='rss_source')]
            logger.info(" Done with configuration for RssFeed of number of sites: {}"\
                    .format(len(self.rss_source_sites)))
        else:
            print("Warning: Couldn't find 'rss_source' secion in the database Setting table")
            logger.warning("Warning: Couldn't find 'rss_source' section in the database Setting table")

        if Setting.objects.filter(section_name='regular_source').exists():
            self.regular_source_sites = [e.setting_value for e in\
                Setting.objects.filter(section_name='regular_source')]
            logger.info(" Done with configuration for regular source, number of sites: {}"\
                    .format(len(self.regular_source_sites)))
        else:
            print("Warning: Couldn't find 'regular_source' secion in the database Setting table")
            logger.warning("Warning: Couldn't find 'regular_source' section in the database Setting table")

        if Setting.objects.filter(section_name='link').exists():
            self.regular_links = [e.setting_value for e in Setting.objects.filter(section_name='link')]
            logger.info(" Done with configuration for regular links number of links: {}"\
                    .format(len(self.regular_links)))
        else:
            print("Warning: Couldn't find 'link' secion in the database Setting table")
            logger.warning("Warning: Couldn't find 'link' in the database Setting table")

        logger.info("Done Initialization")




    # TODO while web crawling I highly recommend using proxy services as well
    # since it will be useful in many various ways.
    # The main reason to use such services is to avoid being detected from the website 
    # and being banned since web crawling is automatic action and might raise suspicions
    # (since most of the web pages doesn???t want you to crawl their data). meanwhile,
    # when using proxies you have a big pool of IPs that are constantly changing
    # so your actions looks more like real human activity,
    # thus you can way easier web crawl web page.
    # TODO drop articles other than english language or mange them
    def download_news(self):

        logger.info("Retrieving news from sites. {} Mode: ".format(self.op_map[self.op_mode]))
        logger.info("Memoize articles is sat " + str(self.n_config.memoize_articles))
        if((self.op_mode == NLP_MODE) or (self.op_mode ==NO_NLP_MODE) ):
            self.papers = [nwp.build(site, config=self.n_config) for site in self.regular_source_sites]
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
                        if len(self.articles)>0 else\
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
        #TODO memoize articles rss
        elif (self.op_mode == RSS_ONLY_MODE):
            self.papers= [ fp.parse(site) for site in self.rss_source_sites]
            self.articles = [x for y in [n.entries for n in self.papers] for x in y] \
                    # filtering is good to be here
            logger.info("RSS: Done parsing news, No Articles" + str(len(self.articles)))
            for article in self.articles:
                article['source_type']='rss'
            logger.info("RSS: Done building a source tag rss, example {}".format(
                str(self.articles[0].get('source_type',"no rss source type found")) \
                        if len(self.articles)>0 else\
                        "no rss has downloaded"))
        else:
            #TODO do rss_crawl with nlp_crawl just changing the site source
            #TODO only the content from newspaper, feedparser better on the rest
            #TODO cut download, ignore existing articles: for the other modes of download
            self.papers= [ fp.parse(site) for site in self.rss_source_sites]
            self.articles = [x for y in [n.entries for n in self.papers] for x in y] \
                    # filtering is good to be here
            article_links= [article.link for article in self.articles]
            logger.info("RSS NLP: Done parsing news, No Articles" + str(len(self.articles)))
            count = 0
            articles_temp=[]
            for article_link in (self.regular_links + article_links):
                if not Article.objects.filter(link=article_link, source_type='rss_nlp').exists():
                    article = NewsPaperArticle(article_link)
                    try:
                        article.download()
                        article.parse()
                        article.nlp()
                        articles_temp.append(article)
                        logger.info("{} articles has downloaded".format(len(articles_temp))) 

                        if len(articles_temp)>20: # pause the download and save to the database
                            logger.info("Cut download is running, cut at Article count of: "\
                                    +str(len(articles_temp)))
                            self.articles = [ a.__dict__ for a in articles_temp] \
                            # change it to dictionary to add source type tag
                            logger.info("RSS NLP: Done with building a dict, NLP: keyword example: "+ \
                            str(self.articles[0].get('keywords',"Nothing found"))\
                                if len(self.articles)>0 else\
                                    "no articles has crawled" )
                            for article in self.articles:
                                article['source_type'] = 'rss_nlp'
                            logger.info("RSS NLP: Done with inserting tag NO NLP: example: "+ \
                            str(self.articles[0].get('source_type',"no source type found"))
                            if len(self.articles)>0 else\
                                "no rss has downloaded")

                            self.serializer(self.articles)
                            articles_temp =[]
                        #TODO download articels in news_pool
                    except:
                        count+=1
                        pass
                else:
                    logger.info("Article already exists in the database.")
            logger.info("RSS NLP: {} articles with bad url has jumped".format(count))
            self.articles = [ a.__dict__ for a in articles_temp] \
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
        self.serializer(self.articles)
        self.prepare_tfidf()


    def serializer(self, articles):
        count=0
        for article in articles:
            random_id = str(uuid.uuid4())
            logger.debug("source url of the article: "+ article['url'])
            if (article['source_type'] !='rss'):
                source_name=re.search('https?://(www\.)?([a-zA-Z0-9]+)?(\.com)?', 
                        article['source_url'])
                date_orignal = (article['publish_date']\
                                    if isinstance(article['publish_date'],datetime.datetime) \
                                    and type(article['publish_date']) != 'str'\
                                    else parser.parse("2012-01-01 00:00:00"))
                logger.debug("The date the article published in:"+str(date_orignal)+str(article['publish_date']))
                article_model = Article(content_id = random_id,
                                title = article['title'],
                                description = article['summary'],
                                authors = article['authors'],
                                date = date_orignal,
                                link = article['url'],
                                top_image = article['top_image'],
                                keywords= str(article['keywords']),
                                source_type = article['source_type'],
                                source=  source_name.group(2) if source_name!= None else 'unknown' ) \
                                        # assigned some old date if the date is None
                try:
                    article_model.save()
                except:
                    count+=1
                    pass
                else:
                    # post the article to the recommendation engine
                    timestamp=time.mktime(datetime.datetime\
                            .strptime(str(date_orignal)[:19], "%Y-%m-%d %H:%M:%S")\
                            .timetuple()) 
                    article_body ={"timestamp": int(timestamp),
                            "content_id": random_id,
                            "author_person_id": "crawler",
                            "author_country": "NA",
                            "url": article['url'],
                            "top_image" : article['top_image'],
                            "title": article['title'],
                            "content": article['summary'],
                            "source":( source_name.group(2) if source_name!= None else 'unknown' ),
                            "community_id": 24}
                    try:
                        response=requests.post(RECOMMENDER_API, data=article_body)
                        logger.info("post request response"+ str(response.reason))
                    except requests.ConnectionError:
                        logger.info("Post request is not sent to the recommendation engine because\
                                of Connection Error")

                    
            else:
                #TODO author of RSS feeds
                if all(a in article for a in ['title','link','summary','published']):
                    article_model = Article(content_id=random_id,
                                    title= article.title,
                                    description = article.summary,
                                    date = (parser.parse(article.published) \
                                            if str(article.published) != "None" \
                                            else parser.parse("2012-01-01 00:00:00")),
                                    link = article.link,
                                    top_image = 'None', 
                                    source_type = article['source_type'],
                                    source='rss') # TODO top image of rss\
                                            # fetched articles
                    try:
                        article_model.save()
                    except:
                        count+=1
                    else:
                        # post the article to the recommendation engine
                        timestamp = time.mktime(datetime.datetime\
                                .strptime(article.published, "%a, %d %b %Y %H:%M:%S GMT")\
                                .timetuple())
                        article_body ={"timestamp": int(timestamp),
                                "content_id": random_id,
                                "author_person_id": "crawler",
                                "author_country": "NA",
                                "url": article.link,
                                "top_image": 'None',
                                "title": article.title,
                                "content": article.summary,
                                "source":'rss',
                                "community_id": 24}
                        try: 
                          response=requests.post(RECOMMENDER_API, data=article_body)
                          logger.info("post request response"+ str(response.text))
                        except requests.ConnectionError:
                            looger.info("Post request is not sent to the recommendation engine because\
                                    of Connection Error")
        logger.info("{} articles has jumped because similar articles already exists"\
                .format(count))
        logger.info("Done with populating the model")

    def prepare_tfidf(self):
        logger.info("Preparing tfidif has started....")
        bag_of_articles=[]

        english_stopset = set(stopwords.words('english')).union(
                  {"things", "that's", "something", "take", "don't", "may", "want", "you're",
                   "set", "might", "says", "including", "lot", "much", "said", "know",
                   "good", "step", "often", "going", "thing", "things", "think",
                  "back", "actually", "better", "look", "find", "right", "example",
                   "verb", "verbs"})
                
        articles= Article.objects.all()
        logger.info("{} articles are in the database which tfiidf is is gonna be prepared for"\
                .format(len(articles)))
        for article in articles:
            if article.title != None and article.description != None and article.keywords != None:
                
                article_words = article.title + " " + article.description + " "+ article.keywords
                cleard = (re.sub("[^a-zA-Z0-9]+", " ", article_words))
                        
                article_tokens = spacy_nlp(article_words)
                article_lemmantized = ' '.join([token.lemma_.lower().strip() \
                                                if token.lemma_ != "-PRON-" else token.lower_ for token in article_tokens ])
                bag_of_articles.append(article_lemmantized)
                

                
            
            elif article.title != None and article['description'] != None:
                article_words = article.title + " "+ article.description
                cleard = (re.sub("[^a-zA-Z0-9]+", " ", article_words))
                        
                article_tokens = spacy_nlp(article['title']+" "+article['description'])
                article_lemmantized = ' '.join([token.lemma_.lower().strip() \
                                    if token.lemma_ != "-PRON-" else token.lower_ for token in article_tokens ])
                bag_of_articles.append(article_lemmantized)
         
        vectorizer = TfidfVectorizer(analyzer='word',
                                            ngram_range=(1, 2),
                                            max_features=10000,
                                            lowercase=True,
                                            stop_words=english_stopset)
        tfidf_matrix = vectorizer.fit_transform(bag_of_articles)
        tfidf= {"matrix":tfidf_matrix, "vectorizer": vectorizer}
        with open('tfidf.pickle', 'wb') as read: 
            pickle.dump(tfidf, read, protocol=pickle.HIGHEST_PROTOCOL) 
        logger.info("Prepare Tfidf is done::::::")
        unlock=cache.delete(self.op_map[self.op_mode]) # release the lock for "a download at 
                                        # some operation mode is to be done one at a time

        logger.debug("Release lock is  done is :"+ str(unlock))

    def search(self, terms, top_results=10):
                articles= Article.objects.all()

                with open('tfidf.pickle', 'rb') as read:
                    tfidf = pickle.load(read) 

                query_tokens= spacy_nlp(terms)
                query_lemmantized = ' '.join([token.lemma_.lower().strip() if\
                        token.lemma_ != "-PRON-" else token.lower_ for token in query_tokens ])

                query_vector= tfidf['vectorizer'].transform([query_lemmantized])

                cosine_similarities = cosine_similarity(query_vector, tfidf['matrix']) 
                #tfidf_matrix_term if it work
                similar = cosine_similarities[0]

                if all(val==0.0 for val in similar):
                    return [{"Nothing found"}]
            
            
                similar_sorted = sorted(similar, reverse=True)
                similar_sorted= [val for val in similar_sorted if val!=0.0]
                similar_sorted=[x.item() for x in similar_sorted]
                similar = [x.item() for x in similar]
        
                

                result= [articles[similar.index(i)] for i in similar_sorted][:min(len(similar_sorted), 
                    top_results)]
                article_serialized = ArticleSerializer([article for article in result], many = True)
                return article_serialized.data
    

