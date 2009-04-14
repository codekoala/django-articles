from django.conf.urls.defaults import *
from django.views.generic import date_based, list_detail
from articles import views

urlpatterns = patterns('',
    (r'^(?P<year>\d{4})/(?P<month>.{3})/(?P<day>\d{1,2})/(?P<slug>.*)/$', views.redirect_to_article),
    url(r'^(?P<year>\d{4})/(?P<month>\d{1,2})/page/(?P<page>\d+)/$', views.display_blog_page, name='articles_in_month_page'),
    url(r'^(?P<year>\d{4})/(?P<month>\d{1,2})/$', views.display_blog_page, name='articles_in_month'),
)

urlpatterns += patterns('',
    url(r'^$', views.display_blog_page, name='articles_archive'),
    url(r'^page/(?P<page>\d+)/$', views.display_blog_page, name='articles_archive_page'),

    url(r'^uncategorized/$', views.display_blog_page, name='articles_uncategorized'),
    url(r'^uncategorized/page/(?P<page>\d+)/$', views.display_blog_page, name='articles_uncategorized_page'),

    url(r'^category/(?P<category>.*)/page/(?P<page>\d+)/$', views.display_blog_page, name='articles_display_category_page'),
    url(r'^category/(?P<category>.*)/$', views.display_blog_page, name='articles_display_category'),

    url(r'^author/(?P<username>.*)/page/(?P<page>\d+)/$', views.display_blog_page, name='articles_by_author_page'),
    url(r'^author/(?P<username>.*)/$', views.display_blog_page, name='articles_by_author'),

    url(r'^(?P<year>\d{4})/(?P<slug>.*)/$', views.display_article, name='articles_display_article'),
)
