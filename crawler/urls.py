from django.urls import path
from crawler import views
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = [
		path('search/<str:terms>/<int:top_results>', views.search_news),
		path('getnews/<str:sort_type>/<int:results>', views.get_news),
                path('getrssfeed/<str:sort_type>/<int:results>',views.get_rss_feed),
                path('trending/', views.trending_topics),
                path('download/', views.download),
]


urlpatterns = format_suffix_patterns(urlpatterns)
