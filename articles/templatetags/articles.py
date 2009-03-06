from django import template
from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from ..models import Article, Category
import datetime, calendar

register = template.Library()

def show_recent_articles(context, count=5):
    articles = Article.objects.active()[:count]
    return {'articles': articles}
register.inclusion_tag('articles/_recent_articles.html', takes_context=True)(show_recent_articles)

def show_categories():
    return {'categories': Category.objects.active(),
            'uncategorized': len(Article.objects.uncategorized())}
register.inclusion_tag('articles/_categories.html')(show_categories)

def get_article_page(article, page=1):
    return article.get_page(page)
register.simple_tag(get_article_page)

def month_counts(year):
    months = [0 for i in range(12)]
    for a in Article.objects.filter(publish_date__year=int(year)):
        months[a.publish_date.month - 1] += 1
    return months

def most_articles_in_a_day(year):
    return max(day_counts(year))
register.simple_tag(most_articles_in_a_day)

def most_articles_in_a_month(year):
    return max(month_counts(year))
register.simple_tag(most_articles_in_a_month)

def articles_in_months(year):
    return ','.join([str(c) for c in month_counts(year)])
register.simple_tag(articles_in_months)
