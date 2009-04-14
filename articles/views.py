from django.conf import settings
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.http import HttpResponsePermanentRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from articles.models import Article, Category
from datetime import datetime

ARTICLE_PAGINATION = getattr(settings, 'ARTICLE_PAGINATION', 20)

def display_blog_page(request, category=None, username=None, year=None, month=None, page=1):
    context = {}

    if category:
        category = get_object_or_404(Category, slug=category)
        articles = category.article_set.all()
        template = 'articles/display_category.html'
        context['category'] = category
    elif username:
        user = get_object_or_404(User, username=username)
        articles = user.article_set.all()
        template = 'articles/by_author.html'
        context['author'] = user
    elif year and month:
        year = int(year)
        month = int(month)
        articles = Article.objects.active().filter(publish_date__year=year, publish_date__month=month)
        template = 'articles/in_month.html'
        context['month'] = datetime(year, month, 1)
    else:
        if request.path.startswith('/uncategorized/'):
            articles = Article.objects.uncategorized()
        else:
            articles = Article.objects.active()
        template = 'articles/article_list.html'

    paginator = Paginator(articles, ARTICLE_PAGINATION,
                          orphans=int(ARTICLE_PAGINATION / 4))
    page = paginator.page(page)

    context.update({'paginator': paginator,
                    'page_obj': page})

    return render_to_response(template,
                              context,
                              context_instance=RequestContext(request))

def display_article(request, year, slug, template='articles/article_detail.html'):
    article = get_object_or_404(Article, publish_date__year=year, slug=slug)
    return render_to_response(template,
                              {'article': article},
                              context_instance=RequestContext(request))

def redirect_to_article(request, year, month, day, slug):
    article = get_object_or_404(Article, publish_date__year=year, slug=slug)
    return HttpResponsePermanentRedirect(article.get_absolute_url())