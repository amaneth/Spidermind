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
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

link_param = openapi.Parameter( 'link', in_=openapi.IN_QUERY, description='link to be crawled', type=openapi.TYPE_STRING, )
fetch_params = [openapi.Parameter('sort', in_=openapi.IN_QUERY, description= "Sort type",
        type= openapi.TYPE_STRING, ),
        openapi.Parameter('results', in_=openapi.IN_QUERY,
            description= "Number of articles to be fetched", type= openapi.TYPE_STRING, ),
        openapi.Parameter('rss', in_=openapi.IN_QUERY, description= "RSS fetch",
        type= openapi.TYPE_BOOLEAN, ),
        openapi.Parameter('nlp', in_=openapi.IN_QUERY, description= "NLP fetch",
        type= openapi.TYPE_BOOLEAN, ),

        ]
#TO DO proper rest api naming
#TO DO class based view
@api_view(['GET'])
def download(request):
    '''
    Download articles from websites based on the mode set in the configuration file and saves to 
    the database.
    Return the downloaded articles plus additional articles in the database
    Get nothing

    Returns: 
            Article(Object): articles fetched from websites

    '''
    if request.method == 'GET':
        s= SNETnews('./news.ini')
        articles= s.download_news()
        count=0
        for article in articles:
            if (article['source_type'] !='rss'):
                article_model = Article(title = article['title'],
                                description = article['summary'],
                                authors = article['authors'],
                                date = (article['publish_date']\
                                        if isinstance(article['publish_date'],datetime.datetime) \
                                        and type(article['publish_date']) != 'str'\
                                        else parser.parse("2012-01-01 00:00:00")),
                                link = article['url'],
                                keywords= str(article['keywords']),
                                source_type = article['source_type']) \
                                        # assigned some old date if the date is None
                try:
                    article_model.save()
                except:
                    count+=1
                    pass
            else:
                #TO DO author of RSS feeds
                if all(a in article for a in ['title','link','summary','published']):
                    article_model = Article(title= article.title,
                                    description = article.summary,
                                    date = (parser.parse(article.published) \
                                            if str(article.published) != "None" \
                                            else parser.parse("2012-01-01 00:00:00")),
                                    link = article.link,
                                    source_type = article['source_type'])
                    try:
                        article_model.save()
                    except:
                        count+=1
                        pass
        logger.info("{} articles has jumped because similar articles already exists"\
                .format(count))
        logger.info("Done with populating the model")
        article_serialized = ArticleSerializer(Article.objects.all(), many=True)
    return Response(article_serialized.data)

@swagger_auto_schema(method ='get',manual_parameters=fetch_params,security=[],
        responses={'400': 'Validation Error','200': ArticleSerializer})
@api_view(['GET'])
def fetch(request):
    '''Return serialized articles in the database 
    Get sort type, results, nlp, rss
    
    This function gets the method of sorting(title or date), the number of articles to be fetched, 
    if RSS fetch is allowed and if NLP fetch is allowed and returns serialized articles. The sorting
    can be title or date. If the number of articles to be fetched is bigger than available in the 
    database, full article available in the database returned. If both rss and nlp are true, articles
    tagged by 'rss_nlp' fetched. if rss is true and nlp is false articles tagged by 'rss' fetched. if
    rss is false and nlp is true articles tagged by nlp fetched. if both rss and nlp are false 
    articles tagged 'crawl'.
    
            Parameters:
                sort_type (str): The method articles returned will be sorted. it can be title or date
                results (int): The number of articles to fetched
                rss (Boolean): if RSS fetch allowed
                nlp (Boolean): if NLP fetch allowed
            
            Returns:
                Article(object): serialized articles
    '''
    if request.method == 'GET':
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

#TO DO returns unrealated news after the exact news needs a fix
#TO DO search can be built from same articles in different modes
#TO DO semantic search engine using NLP
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
                #logger.info("Done Searching. Full Result: " +\
                #        str(dict.(itertools.islice(search_rank.items(), 2))))
                _sel_articles = sorted(search_rank.items(),
                        key=lambda x : x[1],
                        reverse=True)[:min(len(search_rank), top_results)]
                if all(list(map(lambda x : x[1] == 0, _sel_articles))):
                    return JsonResponse({"result":"Nothing Found"})
                article_serialized = ArticleSerializer(dict(_sel_articles).keys(), many = True)
                return Response(article_serialized.data) 

@api_view(['GET'])
def trending_topics(request):
        if request.method == 'GET':
            topics=nwp.hot()
            logger.info("retrieving "+ str(len(topics)) +" trending topics")
            return search_news(request._request,topics,5)

        article_serialized = ArticleSerializer(article_model)
        return Response(article_serialized.data)

@swagger_auto_schema(method ='get',manual_parameters=[link_param],security=[],
        responses={'400': 'Validation Error','200': ArticleSerializer})
@api_view(['GET'])
def article_crawl(request):
    count =0
    if request.method == 'GET':
        link = request.GET["link"]
        article = NewspaperArticle(link)
        article.download()
        article.parse()
        article.nlp()
        article_model = Article(title = article.title,
                                description = article.summary,
                                authors = article.authors,
                                date = (article.publish_date\
                                        if isinstance(article.publish_date ,datetime.datetime) \
                                        and type(article.publish_date) != 'str'\
                                        else parser.parse("2012-01-01 00:00:00")),
                                link = article.url,
                                keywords= str(article.keywords),
                                source_type = 'crawl_nlp') # assigned some old date if the date is None
        try:
            article_model.save()
        except IntegrityError:
            count+=1
            pass
        logger.info("{} articles has jumped because article with the same title already exists"\
                .format(count))
        logger.info("Done with populating the model")
        article_serialized = ArticleSerializer(article_model)
        return Response(article_serialized.data)
