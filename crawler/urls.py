from django.urls import path
from crawler import views
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = [
		path('search/<str:terms>/<int:top_results>', views.search_news),
		path('getnews/<str:sort_type>/<int:results>', views.get_news),
                path('trending', views.trending_topics),
]


urlpatterns = format_suffix_patterns(urlpatterns)
