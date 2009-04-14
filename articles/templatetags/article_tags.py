from django import template
from articles.models import Article, Category
from datetime import datetime

register = template.Library()

class GetCategoriesNode(template.Node):
    def __init__(self, varname):
        self.varname = varname

    def render(self, context):
        categories = Category.objects.active()
        context[self.varname] = categories
        return ''

def get_article_categories(parser, token):
    args = token.split_contents()
    argc = len(args)

    assert argc == 3 and args[1] == 'as'

    return GetCategoriesNode(args[2])

class GetArticlesNode(template.Node):
    def __init__(self, varname, count=None, start=None, end=None, order='desc'):
        self.count = count
        self.start = start
        self.end = end
        self.order = order
        self.varname = varname.strip()

    def render(self, context):
        if self.order and self.order.lower() == 'desc':
            order = '-publish_date'
        else:
            order = 'publish_date'

        articles = Article.objects.active().order_by(order)

        if self.count:
            articles = articles[:self.count]
        else:
            articles = articles[(int(self.start) - 1):int(self.end)]

        if len(articles) == 1: articles = articles[0]

        context[self.varname] = articles
        return ''

def get_articles(parser, token):
    """
    Retrieves a list of Article objects for use in a template.
    """
    args = token.split_contents()
    argc = len(args)

    assert argc in (4,6) or (argc in (5,7) and args[-1].lower() in ('desc', 'asc'))

    order = 'desc'
    count = start = end = varname = None
    if argc == 4: t, count, a, varname = args
    elif argc == 5: t, count, a, varname, order = args
    elif argc == 6: t, start, t, end, a, varname = args
    elif argc == 7: t, start, t, end, a, varname, order = args

    return GetArticlesNode(count=count,
                           start=start,
                           end=end,
                           order=order,
                           varname=varname)

class GetArticleArchivesNode(template.Node):
    def __init__(self, varname):
        self.varname = varname

    def render(self, context):
        archives = {}
        for article in Article.objects.active():
            pub = article.publish_date
            if not archives.has_key(pub.year):
                archives[pub.year] = {}

            archives[pub.year][pub.month] = True

        dt_archives = []
        years = list(int(k) for k in archives.keys())
        years.sort()
        years.reverse()

        for year in years:
            months = []
            m = list(int(k) for k in archives[year].keys())
            m.sort()
            for month in m:
                months.append(datetime(year, month, 1))
            dt_archives.append((
                year, tuple(months)
            ))

        context[self.varname] = dt_archives
        return ''

def get_article_archives(parser, token):
    args = token.split_contents()
    argc = len(args)

    assert argc == 3

    return GetArticleArchivesNode(args[2])

register.tag(get_articles)
register.tag(get_article_categories)
register.tag(get_article_archives)