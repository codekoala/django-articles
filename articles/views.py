from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext, loader, Context
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.conf import settings
from .models import Article, Category
from .forms import SendArticleForm

def list_articles_by_author(request, user_id,
                            template='articles/list_articles_by_author.html'):
    user = get_object_or_404(User, username=user_id)

    return render_to_response(template,
                              {'articles': user.article_set.active(),
                               'author': user},
                              context_instance=RequestContext(request))

def category_detail(request, slug, page=1, \
                    template='articles/category_detail.html', paginate_by=10):
    """
    Displays a blog category and articles that have been assigned to that
    category.  Articles within a given category are paginated by 10 entries.
    """
    category = get_object_or_404(Category,
                                 slug=slug,
                                 is_active=True)

    paginator = Paginator(category.article_set.active(),
                          paginate_by,
                          orphans=5)
    page_obj = paginator.page(int(page))

    return render_to_response(template,
                              {'paginator': paginator,
                               'page_obj': page_obj,
                               'object': category,
                               'is_paginated': (paginator.num_pages > 1)},
                              context_instance=RequestContext(request))

def display_article_page(request, year, month, day, slug, page):
    article = get_object_or_404(Article, slug=slug, is_active=True)

    return render_to_response('articles/article_detail.html',
                              {'object': article, 'page': int(page)},
                              context_instance=RequestContext(request))

def send_article(request, article_id):
    article = get_object_or_404(Article,
                                pk=int(article_id),
                                is_active=True)
    error = None

    if request.method == 'POST':
        form = SendArticleForm(request.POST)
        if form.is_valid():
            site = Site.objects.get_current()
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']

            c = Context({
                'article': article,
                'sender': {
                    'name': name,
                    'email': email
                },
                'message': form.cleaned_data['message'],
                'site': site,
            })
            t = loader.get_template('articles/send_article_email.txt')

            subject = '%s %s has sent you an article on %s!' % (settings.EMAIL_SUBJECT_PREFIX,
                                                                name, site.name)
            message = t.render(c)

            try:
                for r in form.cleaned_data['receivers'].split(','):
                    send_mail(subject, message, email, [r.strip()])
            except:
                error = 'Failed to send article to %s' % r
            else:
                error = '%s was sent to all recipients' % article.title

                return HttpResponseRedirect(article.get_absolute_url())
    else:
        form = SendArticleForm()

    return render_to_response('articles/send_article.html',
                              {'form': form,
                               'article': article,
                               'error': error},
                              context_instance=RequestContext(request))
