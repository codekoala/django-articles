from django import template
from django.core.cache import cache
from django.core.urlresolvers import resolve, reverse, Resolver404
from django.db.models import Count
from articles.models import Article, Tag
from datetime import datetime
import math

register = template.Library()

class GetCategoriesNode(template.Node):
    """
    Retrieves a list of live article tags and places it into the context
    """
    def __init__(self, varname):
        self.varname = varname

    def render(self, context):
        tags = Tag.objects.all()
        context[self.varname] = tags
        return ''

def get_article_tags(parser, token):
    """
    Retrieves a list of live article tags and places it into the context
    """
    args = token.split_contents()
    argc = len(args)

    try:
        assert argc == 3 and args[1] == 'as'
    except AssertionError:
        raise template.TemplateSyntaxError('get_article_tags syntax: {% get_article_tags as varname %}')

    return GetCategoriesNode(args[2])

class GetArticlesNode(template.Node):
    """
    Retrieves a set of article objects.

    Usage::

        {% get_articles 5 as varname %}

        {% get_articles 5 as varname asc %}

        {% get_articles 1 to 5 as varname %}

        {% get_articles 1 to 5 as varname asc %}
    """
    def __init__(self, varname, count=None, start=None, end=None, order='desc'):
        self.count = count
        self.start = start
        self.end = end
        self.order = order
        self.varname = varname.strip()

    def render(self, context):
        # determine the order to sort the articles
        if self.order and self.order.lower() == 'desc':
            order = '-publish_date'
        else:
            order = 'publish_date'

        user = context.get('user', None)

        # get the live articles in the appropriate order
        articles = Article.objects.live(user=user).order_by(order).select_related()

        if self.count:
            # if we have a number of articles to retrieve, pull the first of them
            articles = articles[:int(self.count)]
        else:
            # get a range of articles
            articles = articles[(int(self.start) - 1):int(self.end)]

        # don't send back a list when we really don't need/want one
        if len(articles) == 1 and not self.start and int(self.count) == 1:
            articles = articles[0]

        # put the article(s) into the context
        context[self.varname] = articles
        return ''

def get_articles(parser, token):
    """
    Retrieves a list of Article objects for use in a template.
    """
    args = token.split_contents()
    argc = len(args)

    try:
        assert argc in (4,6) or (argc in (5,7) and args[-1].lower() in ('desc', 'asc'))
    except AssertionError:
        raise template.TemplateSyntaxError('Invalid get_articles syntax.')

    # determine what parameters to use
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
    """
    Retrieves a list of years and months in which articles have been posted.
    """
    def __init__(self, varname):
        self.varname = varname

    def render(self, context):
        cache_key = 'article_archive_list'
        dt_archives = cache.get(cache_key)
        if dt_archives is None:
            archives = {}
            user = context.get('user', None)

            # iterate over all live articles
            for article in Article.objects.live(user=user).select_related():
                pub = article.publish_date

                # see if we already have an article in this year
                if not archives.has_key(pub.year):
                    # if not, initialize a dict for the year
                    archives[pub.year] = {}

                # make sure we know that we have an article posted in this month/year
                archives[pub.year][pub.month] = True

            dt_archives = []

            # now sort the years, so they don't appear randomly on the page
            years = list(int(k) for k in archives.keys())
            years.sort()

            # more recent years will appear first in the resulting collection
            years.reverse()

            # iterate over all years
            for year in years:
                # sort the months of this year in which articles were posted
                m = list(int(k) for k in archives[year].keys())
                m.sort()

                # now create a list of datetime objects for each month/year
                months = [datetime(year, month, 1) for month in m]

                # append this list to our final collection
                dt_archives.append( ( year, tuple(months) ) )

            cache.set(cache_key, dt_archives)

        # put our collection into the context
        context[self.varname] = dt_archives
        return ''

def get_article_archives(parser, token):
    """
    Retrieves a list of years and months in which articles have been posted.
    """
    args = token.split_contents()
    argc = len(args)

    try:
        assert argc == 3 and args[1] == 'as'
    except AssertionError:
        raise template.TemplateSyntaxError('get_article_archives syntax: {% get_article_archives as varname %}')

    return GetArticleArchivesNode(args[2])

class DivideObjectListByNode(template.Node):
    """
    Divides an object list by some number to determine now many objects will
    fit into, say, a column.
    """
    def __init__(self, object_list, divisor, varname):
        self.object_list = template.Variable(object_list)
        self.divisor = template.Variable(divisor)
        self.varname = varname

    def render(self, context):
        # get the actual object list from the context
        object_list = self.object_list.resolve(context)

        # get the divisor from the context
        divisor = int(self.divisor.resolve(context))

        # make sure we don't divide by 0 or some negative number!!!!!!
        assert divisor > 0

        context[self.varname] = int(math.ceil(len(object_list) / float(divisor)))
        return ''

def divide_object_list(parser, token):
    """
    Divides an object list by some number to determine now many objects will
    fit into, say, a column.
    """
    args = token.split_contents()
    argc = len(args)

    try:
        assert argc == 6 and args[2] == 'by' and args[4] == 'as'
    except AssertionError:
        raise template.TemplateSyntaxError('divide_object_list syntax: {% divide_object_list object_list by divisor as varname %}')

    return DivideObjectListByNode(args[1], args[3], args[5])

class GetPageURLNode(template.Node):
    """
    Determines the URL of a pagination page link based on the page from which
    this tag is called.
    """
    def __init__(self, page_num, varname=None):
        self.page_num = template.Variable(page_num)
        self.varname = varname

    def render(self, context):
        url = None

        # get the page number we're linking to from the context
        page_num = self.page_num.resolve(context)

        try:
            # determine what view we are using based upon the path of this page
            view, args, kwargs = resolve(context['request'].path)
        except (Resolver404, KeyError):
            raise ValueError('Invalid pagination page.')
        else:
            # set the page parameter for this view
            kwargs['page'] = page_num

            # get the new URL from Django
            url = reverse(view, args=args, kwargs=kwargs)

        if self.varname:
            # if we have a varname, put the URL into the context and return nothing
            context[self.varname] = url
            return ''

        # otherwise, return the URL directly
        return url

def get_page_url(parser, token):
    """
    Determines the URL of a pagination page link based on the page from which
    this tag is called.
    """
    args = token.split_contents()
    argc = len(args)
    varname = None

    try:
        assert argc in (2, 4)
    except AssertionError:
        raise template.TemplateSyntaxError('get_page_url syntax: {% get_page_url page_num as varname %}')

    if argc == 4: varname = args[3]

    return GetPageURLNode(args[1], varname)

def tag_cloud():
    """Provides the tags with a "weight" attribute to build a tag cloud"""

    cache_key = 'tag_cloud_tags'
    tags = cache.get(cache_key)
    if tags is None:
        MAX_WEIGHT = 7
        tags = Tag.objects.annotate(count=Count('article'))

        if len(tags) == 0:
            # go no further
            return {}

        min_count = max_count = tags[0].article_set.count()
        for tag in tags:
            if tag.count < min_count:
                min_count = tag.count
            if max_count < tag.count:
                max_count = tag.count

        # calculate count range, and avoid dbz
        _range = float(max_count - min_count)
        if _range == 0.0:
            _range = 1.0

        # calculate tag weights
        for tag in tags:
            tag.weight = int(MAX_WEIGHT * (tag.count - min_count) / _range)

        cache.set(cache_key, tags)

    return {'tags': tags}

# register dem tags!
register.tag(get_articles)
register.tag(get_article_tags)
register.tag(get_article_archives)
register.tag(divide_object_list)
register.tag(get_page_url)
register.inclusion_tag('articles/_tag_cloud.html')(tag_cloud)
