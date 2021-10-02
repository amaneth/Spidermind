import logging
import logging.handlers as loghandlers

import datetime
from dateutil import parser
import string
import newspaper as nwp

from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import api_view
from rest_framework.parsers import JSONParser 
from crawler.models import Article
from crawler.serializers import ArticleSerializer
from crawler.utils.news import SNETnews
from django.db import IntegrityError

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
loghandle = loghandlers.TimedRotatingFileHandler(
                filename="SNETnews.log",
                when='D', interval=1, backupCount=7,
                encoding="utf-8")
loghandle.setFormatter(
    logging.Formatter("%(asctime)s %(message)s"))
logger.addHandler(loghandle)


@api_view(['GET'])
def download(request):
    if request.method == 'GET':
        s= SNETnews('./news.ini')
        articles= s.download_news()
        count=0
        for article in articles:
            if (article['source_type'] == 'crawl'):
                article_model = Article(title = article['title'],
                                description = article['summary'],
                                authors = article['authors'],
                                date = (article['publish_date']\
                                        if isinstance(article['publish_date'],datetime.datetime) \
                                        and type(article['publish_date']) != 'str'\
                                        else parser.parse("2012-01-01 00:00:00")),
                                link = article['url'],
                                keywords= str(article['keywords']),
                                source_type = 'crawl') # assigned some old date if the date is None
                try:
                    article_model.save()
                except IntegrityError:
                    count+=1
                    pass
            elif (article['source_type'] == 'rss'):
                if all(a in article for a in ['title','link','summary','published']):
                    article_model = Article(title= article.title,
                                    description = article.summary,
                                    date = (parser.parse(article.published) \
                                            if str(article.published) != "None" \
                                            else parser.parse("2012-01-01 00:00:00")),
                                    link = article.link,
                                    source_type = 'rss')
                    try:
                        article_model.save()
                    except IntegrityError:
                        count+=1
                        pass
        logger.info("{} articles has jumped because article with the same title already exists"\
                .format(count))
        logger.info("Done with populating the model")
        article_serialized = ArticleSerializer(Article.objects.all(), many = True)
    return JsonResponse(article_serialized.data, safe= False)

@api_view(['GET'])
def get_news(request, sort_type="title", results=10):
        if request.method == 'GET':
                articles= Article.objects.filter(source_type='crawl')
                if sort_type == "title":
                    logger.info("Sort Type: title, No Articles: " + str(len(articles)))
                    articles = sorted(articles,
                            key=lambda x : x.title)[:min(results, len(articles))]
                elif sort_type == "date":
                    articles = sorted(articles,
                            key= lambda x : x.date.timestamp(),\
                                    reverse=True)[:min(results, len(articles))]
                article_serialized= ArticleSerializer(articles, many=True)
                return JsonResponse(article_serialized.data, safe= False)

@api_view(['GET'])
def search_news(request, terms, top_results=1):
    if request.method == 'GET':
                search_index = {}
                search_rank = {}
                articles= Article.objects.all()
                for article in articles: 
                        if article.title != None and article.description\
                                != None and article.keywords != None :
                            search_index[article] = list(article.keywords) \
                                    + article.title.translate(
                                        str.maketrans(
                                            '', '', string.punctuation)).split(" ") \
                                    + article.description.translate(
                                    str.maketrans(
                                            '', '', string.punctuation)).split(" ")
                        elif article != None and article.description !=None:
                            self.search_index[article] = \
                                article.title.translate(
                                    str.maketrans(
                                        '', '', string.punctuation)).split(" ") \
                                + article.description.translate(
                                    str.maketrans(
                                        '', '', string.punctuation)).split(" ")
                logger.info("Starting Search for " + str(len(terms)) + \
                        " and top results: " + str(top_results)) # improve seach lemmantizing words
                if isinstance(terms,str):
                    terms=[terms]
                for article,keywords in search_index.items():
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
                    return JsonResponse({"result":"Nothing Found"})
                article_serialized = ArticleSerializer(dict(_sel_articles).keys(), many = True)
                return JsonResponse(article_serialized.data, safe=False) # safe = True

@api_view(['GET'])
def trending_topics(request):
        if request.method == 'GET':
            topics=nwp.hot()
            logger.info("retrieving "+ str(len(topics)) +" trending topics")
            return search_news(request._request,topics,5)
@api_view(['GET'])            
def get_rss_feed(request, sort_type="title", results=10):
    if request.method == 'GET':
                articles= Article.objects.filter(source_type='rss')
                if sort_type == "title":
                    logger.info("Sort Type: title, No Articles: " + str(len(articles)))
                    articles = sorted(articles,
                            key=lambda x : x.title)[:min(results, len(articles))]
                elif sort_type == "date":
                    articles= sorted(articles,
                            key= lambda x : x.date.timestamp(),\
                                    reverse=True)[:min(results, len(articles))]
                article_serialized= ArticleSerializer(articles, many=True)
                return JsonResponse(article_serialized.data, safe = False)

