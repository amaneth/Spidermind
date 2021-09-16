import logging
import logging.handlers as loghandlers

from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import api_view
from rest_framework.parsers import JSONParser 
from crawler.models import Article
from crawler.serializers import ArticleSerializer
from crawler.utils.news import SNETnews

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
        for article in articles:
            if (article['source_type'] == 'crawl'):
                article_model = Article(title = article['title'],
                                description = article['summary'],
                                authors = article['authors'],
                                date = str(article['publish_date']),
                                link = article['url'],
                                keywords= str(article['keywords']),
                                source_type = 'crawl')
                article_model.save()
            elif (article['source_type'] == 'rss'):
                if all(a in article for a in ['title','link','summary','published']):
                    article_model = Article(title= article.title,
                                    description = article.summary,
                                    date = str(article.published),
                                    link = article.link,
                                    source_type = 'rss')
                    article_model.save()
        logger.info("Done with populating the model")
        article_serialized = ArticleSerializer(Article.objects.all(), many = True)
    return JsonResponse(article_serialized.data, safe= False)

@api_view(['GET'])
def get_news(request, sort_type="title", results=10):
	if request.method == 'GET':	
		s= SNETnews('./news.ini')
		s.download_news()
		articles=s.get_news(sort_type,results)
		print(type(articles))
		for article in articles:
			article_model= Article(title= article.title,
				description = article.summary,
				authors = article.authors, 
				date = str(article.publish_date),
				link = article.url)
			article_model.save()
		article_serialized= ArticleSerializer(Article.objects.all(), many=True)
		return JsonResponse(article_serialized.data, safe= False)

@api_view(['GET'])
def search_news(request, terms, top_results=1):
	if request.method == 'GET':
		s = SNETnews()
		s.download_news()
		articles= s.search_news(terms, top_results)
		for article in articles: 
			article_model = Article(title = article.title,
						description= article.summary,
						authors = article.authors,
						date = str(article.publish_date),
						link = article.url)
			article_model.save()
		article_serialized = ArticleSerializer(Article.objects.all(), many = True)
		return JsonResponse(article_serialized.data, safe=False)

@api_view(['GET'])
def trending_topics(request):
	if request.method == 'GET':
		s= SNETnews()
		s.download_news()
		articles = s.trending_topics()
		for article in articles:
			article_model = Article(title = article.title,
						description = article.summary,
						authors = article.authors,
						date = str(article.publish_date),
						link = article.url)
			article_model.save()
		article_serialized = ArticleSerializer(Article.objects.all(), many=True)
		return JSONResponse(article_serialized.data, safe=False)
@api_view(['GET'])            
def get_rss_feed(request, sort_type="title", results=10):
    if request.method == 'GET':
        s = SNETnews('./news.ini')
        #s.download_news()
        articles = s.get_rss_feed(sort_type, results)
        for article in articles:
            article_model = Article(title= article.title, 
                                    description = article.summary,
                                    date = str(article.published),
                                    link = article.link)
            article_model.save()
        article_serialized = ArticleSerializer(Article.objects.all(), many = True)
        return JsonResponse(article_serialized.data, safe = False)

