import logging
import logging.handlers as loghandlers

import datetime
from dateutil import parser
import string
import newspaper as nwp
from newspaper import Article as NewspaperArticle
import itertools

from rest_framework.response import Response
from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser 
from crawler.models import Article
from crawler.serializers import ArticleSerializer
from crawler.utils.news import SNETnews
from django.db import IntegrityError
from django_celery_beat.models import PeriodicTask, IntervalSchedule


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
loghandle = loghandlers.TimedRotatingFileHandler(
                filename="SNETnews.log",
                when='D', interval=1, backupCount=7,
                encoding="utf-8")
loghandle.setFormatter(
    logging.Formatter("%(asctime)s %(message)s"))
logger.addHandler(loghandle)
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

link_param = openapi.Parameter( 'link', in_=openapi.IN_QUERY, description='link to be crawled',
        type=openapi.TYPE_STRING, )
auto_refresh_param = openapi.Parameter( 'enable', in_=openapi.IN_QUERY,
        description='if set true auto refresh will be on',type=openapi.TYPE_BOOLEAN, )
fetch_params = [openapi.Parameter('sort', in_=openapi.IN_QUERY, description= "Sort type",
        type= openapi.TYPE_STRING, ),
        openapi.Parameter('results', in_=openapi.IN_QUERY,
            description= "Number of articles to be fetched", type= openapi.TYPE_STRING, ),
        openapi.Parameter('rss', in_=openapi.IN_QUERY, description= "RSS fetch",
        type= openapi.TYPE_BOOLEAN, ),
        openapi.Parameter('nlp', in_=openapi.IN_QUERY, description= "NLP fetch",
        type= openapi.TYPE_BOOLEAN, ),

        ]
search_params= [openapi.Parameter('terms', in_=openapi.IN_QUERY,
            description= "text to be searched", type= openapi.TYPE_STRING, ),
            openapi.Parameter('results', in_=openapi.IN_QUERY,
                description= "Top n articles to be returned", type= openapi.TYPE_STRING, ),]

snet= SNETnews('./news.ini')



#TODO proper rest api naming
#TODO class based view
#TODO Ensuring a task is only executed one at a time, celery scheduling 
class Refresh(APIView):
    '''
    Download articles from websites based on the mode set in the configuration file and saves to
    the database.
    Return the downloaded articles plus additional articles in the database
    Get nothing

    Returns:
            Article(Object): articles fetched from websites

    '''
    def get(self, request, format=None):
        article_serialized= snet.download_news()
        return Response(article_serialized.data)




class Fetch(APIView):

    @swagger_auto_schema(manual_parameters=fetch_params,security=[],
            responses={'400': 'Validation Error','200': ArticleSerializer})
    def get(self, request, format=None):
        '''Return serialized articles in the database 
        Get sort type, results, nlp, rss
        
        This function gets the method of sorting(title or date), the number of articles
        to be fetched, if RSS fetch is allowed and if NLP fetch is allowed and
        returns serialized articles.The sorting can be title or date. If the number of 
        articles to be fetched is bigger than available in the database, full article
        available in the database returned. If both rss and nlp are true, articlestagged by
        'rss_nlp' fetched. if rss is true and nlp is false articles tagged by 'rss' fetched. if
        rss is false and nlp is true articles tagged by nlp fetched. if both rss and nlp are false 
        articles tagged 'crawl'.
        
                Parameters:
                    sort_type (str): The method articles returned will be sorted.
                    it can be title or date
                    results (int): The number of articles to fetched
                    rss (Boolean): if RSS fetch allowed
                    nlp (Boolean): if NLP fetch allowed
                
                Returns:
                    Article(object): serialized articles
        '''
        sort_type = request.GET['sort']
        results = int(request.GET['results'])
        rss = True if request.GET['rss']=='true' else False
        nlp = True if request.GET['nlp']=='true' else False
        source_map = {(False, False): 'crawl', 
                        (False, True):'crawl_nlp', 
                        (True, False): 'rss',
                        (True, True): 'rss_nlp' }
        articles= Article.objects.filter(source_type=source_map[(rss, nlp)])
        if sort_type == "title":
            logger.info("Sort Type: title, No Articles: " + str(len(articles)))
            articles = sorted(articles,
                    key=lambda x : x.title)[:min(results, len(articles))]
        elif sort_type == "date":
            articles = sorted(articles,
                    key= lambda x : x.date.timestamp(),\
                            reverse=True)[:min(results, len(articles))]
        article_serialized= ArticleSerializer(articles, many=True)
        return Response(article_serialized.data)




#TODO returns unrealated news after the exact news needs a fix
#TODO search index can be built from same articles in different modes
#TODO semantic search engine using NLP
class SearchNews(APIView):
    @swagger_auto_schema(manual_parameters=search_params,security=[],
            responses={'400': 'Validation Error','200': ArticleSerializer})
    def get(self, request, format=None):
        terms = request.GET['terms'].split(",")
        logger.info('{}--- are the terms to be searched'.format(type(terms)))
        top_results= int(request.GET['results'])
        search_index = {}
        search_rank = {}
        article_serialized = snet.search(terms, top_results)
        return Response(article_serialized) 



class Trending(APIView):
    def get(self, request, format=None):
                topics=nwp.hot()
                logger.info("retrieving "+ str(len(topics)) +" trending topics")
                article_serialized = snet.search(topics)
                return Response(article_serialized)



class ArticleCrawl(APIView):
    @swagger_auto_schema(manual_parameters=[link_param],security=[],
            responses={'400': 'Validation Error','200': ArticleSerializer})
    def get(self, request):
        count =0
        if request.method == 'GET':
            link = request.GET["link"]
            article_serialized = snet.article_crawl(link)
            return Response(article_serialized.data)



class AutoRefresh(APIView):
    @swagger_auto_schema(manual_parameters=[auto_refresh_param],security=[],
            responses={'400': 'Validation Error','200': ArticleSerializer})
    def get(self, request):
            start = True if request.GET['enable']=='true' else False
            periodic_task = PeriodicTask.objects.get(name='refreshing the database')
            periodic_task.enabled = start
            periodic_task.save()
            return Response({'enable':str(start)})

