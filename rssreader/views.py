from django.shortcuts import render

from django import HttpResponse

# Create your views here.
Class RSSreader:
    def __init__(self):
        self.feed
    def reader(self, request):
        if request.method='GET':
            url=request.GET["url"]
            self.feed = feedparser.parse(url)
        else:
            feed=None

        return(HttpRespnse({'feed': feed,})  
