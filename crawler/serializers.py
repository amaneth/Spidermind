from rest_framework import serializers
from crawler.models import Article


class ArticleSerializer(serializers.ModelSerializer):
	class Meta:
		model = Article
		fields = ['title', 'description','authors', 'date', 'link', 'source_type']
