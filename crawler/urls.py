from django.urls import path
from crawler import views
from rest_framework.urlpatterns import format_suffix_patterns

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

...

schema_view = get_schema_view(
   openapi.Info(
      title="The crawler",
      default_version='v1',
      description="An api to crawl websites",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@snippets.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
		path('search/<str:terms>/<int:top_results>', views.search_news),
                path('nlp/<str:sort_type>/<int:results>', views.get_news_nlp),
                path('no_nlp<str:sort_type>/<int:results>', views.get_news_no_nlp),
                path('rss_nlp<str:sort_type>/<int:results>',views.get_rss_nlp),
                path('rss/<str:sort_type>/<int:results>',views.get_rss_feed),
                path('trending/', views.trending_topics),
                path('download/', views.download),
                path('singlearticle/', views.single_article_crawl),
                path('', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
                path('redoc', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

]


urlpatterns = format_suffix_patterns(urlpatterns)
