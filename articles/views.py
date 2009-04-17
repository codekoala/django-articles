from django.conf import settings
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.http import HttpResponsePermanentRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from articles.models import Article, Category
from datetime import datetime

ARTICLE_PAGINATION = getattr(settings, 'ARTICLE_PAGINATION', 20)

def display_blog_page(request, category=None, username=None, year=None, month=None, page=1):
    """
    Handles all of the magic behind the pages that list articles in any way.
    Yes, it's dirty to have so many URLs go to one view, but I'd rather do that
    than duplicate a bunch of code.  I'll probably revisit this in the future.
    """
    context = {}

    if category:
        # listing articles in a category
        if category == 'uncategorized':
            articles = Article.objects.uncategorized()
            template = 'articles/uncategorized_article_list.html'
        else:
            category = get_object_or_404(Category, slug=category)
            articles = category.article_set.active()
            template = 'articles/display_category.html'
            context['category'] = category
    elif username:
        # listing articles by a particular author
        user = get_object_or_404(User, username=username)
        articles = user.article_set.active()
        template = 'articles/by_author.html'
        context['author'] = user
    elif year and month:
        # listing articles in a given month and year
        year = int(year)
        month = int(month)
        articles = Article.objects.active().filter(publish_date__year=year, publish_date__month=month)
        template = 'articles/in_month.html'
        context['month'] = datetime(year, month, 1)
    else:
        # listing articles with no particular filtering
        articles = Article.objects.active()
        template = 'articles/article_list.html'

    # paginate the articles
    paginator = Paginator(articles, ARTICLE_PAGINATION,
                          orphans=int(ARTICLE_PAGINATION / 4))
    page = paginator.page(page)

    context.update({'paginator': paginator,
                    'page_obj': page})

    return render_to_response(template,
                              context,
                              context_instance=RequestContext(request))

def display_article(request, year, slug, template='articles/article_detail.html'):
    """
    Displays a single article.
    """

    try:
        article = Article.objects.active().get(publish_date__year=year, slug=slug)
    except Article.DoesNotExist:
        raise Http404

    # make sure the user is logged in if the article requires it
    if article.login_required and not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('auth_login') + '?next=' + request.path)

    return render_to_response(template,
                              {'article': article},
                              context_instance=RequestContext(request))

def redirect_to_article(request, year, month, day, slug):
    # this is a little snippet to handle URLs that are formatted the old way.
    article = get_object_or_404(Article, publish_date__year=year, slug=slug)
    return HttpResponsePermanentRedirect(article.get_absolute_url())
