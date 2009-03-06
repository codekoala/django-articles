from django.conf.urls.defaults import *
from django.views.generic import date_based, list_detail
from .models import Category, Article
import views
from datetime import datetime

categories = {
    'queryset': Category.objects.active().iterator(),
}

articles = {
    'queryset': Article.objects.active().iterator(),
    'date_field': 'publish_date',
    'extra_context': {'page': 1},
}

uncategorized = {
    'queryset': Article.objects.uncategorized(),
    'paginate_by': 10,
    'allow_empty': True,
    'template_name': 'articles/article_list_uncategorized.html'
}

articles_month = articles.copy()
articles_month['allow_empty'] = True

articles_year = articles_month.copy()
articles_year['make_object_list'] = True

articles_archive = articles_month.copy()
articles_archive['paginate_by'] = 10
del articles_archive['date_field']

urlpatterns = patterns('',
    url(r'^author/(?P<user_id>[-\w]+)/$',
        views.list_articles_by_author, name='articles_by_author'),

    # categories
    url(r'^category/(?P<slug>[-\w]+)/$',
        views.category_detail, name='articles_display_category'),
    url(r'^category/(?P<slug>[-\w]+)/page/(?P<page>\d+)/$',
        views.category_detail, name='articles_display_category_page'),
    url(r'^uncategorized/$',
        list_detail.object_list, uncategorized, name='articles_display_uncategorized'),
    url(r'^uncategorized/page/(?P<page>\d+)/$',
        list_detail.object_list, uncategorized, name='articles_display_uncategorized_page'),

    # articles
    url(r'^(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/(?P<slug>[-\w]+)/',
        date_based.object_detail, articles, name='articles_display_article'),
    url(r'^(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/$',
        date_based.archive_day, articles_month, name='articles_day_archive'),
    url(r'^(?P<year>\d{4})/(?P<month>[a-z]{3})/$',
        date_based.archive_month, articles_month, name='articles_month_archive'),
    url(r'^(?P<year>\d{4})/$',
        date_based.archive_year, articles_year, name='articles_year_archive'),

    url(r'^$',
        list_detail.object_list, articles_archive, name='articles_archive'),
    url(r'^page/(?P<page>\d+)/$',
        list_detail.object_list, articles_archive, name='articles_archive_page'),

    url(r'^send/article/(?P<article_id>\d+)/$', views.send_article, name='send_article'),
)
