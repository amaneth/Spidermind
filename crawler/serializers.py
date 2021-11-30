from rest_framework import serializers
from crawler.models import Article


class ArticleSerializer(serializers.ModelSerializer):
	class Meta:
		model = Article
		fields = ['content_id','title', 'description','authors', 'date', 'link','top_image','keywords', 'source_type','source']
