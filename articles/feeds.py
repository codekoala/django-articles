from django.conf import settings
from django.contrib.syndication.views import Feed, FeedDoesNotExist
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.utils.feedgenerator import Atom1Feed

from articles.models import Article, Tag

# default to 24 hours for feed caching
FEED_TIMEOUT = getattr(settings, 'ARTICLE_FEED_TIMEOUT', 86400)

class SiteMixin(object):

    @property
    def site(self):
        if not hasattr(self, '_site'):
            self._site = Site.objects.get_current()

        return self._site

class LatestEntries(Feed, SiteMixin):

    def title(self):
        return "%s Articles" % (self.site.name,)

    def link(self):
        return reverse('articles_archive')

    def items(self):
        key = 'latest_articles'
        articles = cache.get(key)

        if articles is None:
            articles = list(Article.objects.live().order_by('-publish_date')[:15])
            cache.set(key, articles, FEED_TIMEOUT)

        return articles

    def item_author_name(self, item):
        return item.author.username

    def item_pubdate(self, item):
        return item.publish_date

class TagFeed(Feed, SiteMixin):

    def get_object(self, request, slug):
        try:
            return Tag.objects.get(slug__iexact=slug)
        except Tag.DoesNotExist:
            raise FeedDoesNotExist

    def title(self, obj):
        return "%s: Newest Articles Tagged '%s'" % (self.site.name, obj.name)

    def link(self, obj):
        return obj.get_absolute_url()

    def description(self, obj):
        return "Articles Tagged '%s'" % obj.name

    def items(self, obj):
        return self.item_set(obj)[:10]

    def item_set(self, obj):
        key = 'articles_for_%s' % obj.name
        articles = cache.get(key)

        if articles is None:
            articles = list(obj.article_set.live().order_by('-publish_date'))
            cache.set(key, articles, FEED_TIMEOUT)

        return articles

    def item_author_name(self, item):
        return item.author.username

    def item_author_link(self, item):
        return reverse('articles_by_author', args=[item.author.username])

    def item_pubdate(self, item):
        return item.publish_date

class LatestEntriesAtom(LatestEntries):
    feed_type = Atom1Feed

class TagFeedAtom(TagFeed):
    feed_type = Atom1Feed
