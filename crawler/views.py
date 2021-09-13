from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser 
from crawler.models import Article
from crawler.serializers import ArticleSerializer
from crawler.utils.news import SNETnews


@csrf_exempt

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
