from django.db import models, connection
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.contrib.sitemaps import ping_google
from django.contrib.markup.templatetags import markup
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from datetime import datetime
from base64 import encodestring
import os
import re
import urllib
import unicodedata

WORD_LIMIT = getattr(settings, 'ARTICLES_TEASER_LIMIT', 75)
MARKUP_OPTIONS = getattr(settings, 'ARTICLE_MARKUP_OPTIONS', (
        ('h', _('HTML/Plain Text')),
        ('m', _('Markdown')),
        ('r', _('ReStructured Text')),
        ('t', _('Textile'))
    ))
MARKUP_DEFAULT = getattr(settings, 'ARTICLE_MARKUP_DEFAULT', 'h')

# regex used to find links in an article
LINK_RE = re.compile('<a.*?href="(.*?)".*?>(.*?)</a>', re.I|re.M)
TITLE_RE = re.compile('<title>(.*?)</title>', re.I|re.M)

def get_name(user):
    """
    Provides a way to fall back to a user's username if their full name has not
    been entered.
    """
    if len(user.get_full_name().strip()):
        return user.get_full_name()
    else:
        return user.username
User.get_name = get_name

class CategoryManager(models.Manager):
    def active(self):
        return self.get_query_set().filter(is_active=True)

class Category(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True, blank=True)

    objects = CategoryManager()

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('articles_display_category', args=(self.slug,))

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'categories'

class ArticleManager(models.Manager):
    def active(self):
        """
        Retrieves all active articles which have been published and have not yet
        expired.
        """
        now = datetime.now()
        return self.get_query_set().filter(
                Q(expiration_date__isnull=True) |
                Q(expiration_date__gte=now),
                publish_date__lte=now,
                is_active=True)

    def uncategorized(self):
        """
        Find all articles that were not assigned a category.
        """

        return self.active().filter(categories__isnull=True)

class Article(models.Model):
    title = models.CharField(max_length=100)
    slug = models.SlugField(unique_for_year='publish_date')
    author = models.ForeignKey(User)

    keywords = models.TextField(blank=True)
    description = models.TextField(blank=True, help_text=_("If omitted, the description will be determined by the first bit of the article's content."))

    markup = models.CharField(max_length=1, choices=MARKUP_OPTIONS, default=MARKUP_DEFAULT, help_text=_('Select the type of markup you are using in this article.'))
    content = models.TextField()
    rendered_content = models.TextField()

    categories = models.ManyToManyField(Category, help_text=_('Select any categories to classify the content of this article.'), blank=True)
    followup_for = models.ManyToManyField('self', symmetrical=False, blank=True, help_text=_('Select any other articles that this article follows up on.'), related_name='followups')
    related_articles = models.ManyToManyField('self', blank=True)

    publish_date = models.DateTimeField(default=datetime.now, help_text=_('The date and time this article shall appear online.'))
    expiration_date = models.DateTimeField(blank=True, null=True, help_text=_('Leave blank if the article does not expire.'))

    is_active = models.BooleanField(default=True, blank=True)
    is_commentable = models.BooleanField(default=True, blank=True)
    login_required = models.BooleanField(blank=True, help_text=_('Enable this if users must login before they can read this article.'))

    objects = ArticleManager()

    def __init__(self, *args, **kwargs):
        """
        Make sure that we have some rendered content to use.
        """
        super(Article, self).__init__(*args, **kwargs)

        if self.id:
            if not self.rendered_content or not len(self.rendered_content.strip()):
                self.save()

    def __unicode__(self):
        return self.title

    def save(self):
        """
        Renders the article using the appropriate markup language.  Pings
        Google to let it know that this article has been updated.
        """
        if self.markup == 'm':
            self.rendered_content = markup.markdown(self.content)
        elif self.markup == 'r':
            self.rendered_content = markup.restructuredtext(self.content)
        elif self.markup == 't':
            self.rendered_content = markup.textile(self.content)
        else:
            self.rendered_content = self.content

        if not settings.DEBUG:
            # try to tell google that we have a new article
            try:
                ping_google()
            except Exception:
                pass

    def _get_article_links(self):
        links = {}

        for link in LINK_RE.finditer(self.rendered_content):
            key = 'href_title_' + encodestring(link.group(1)).strip()
            if not cache.get(key):
                c = urllib.urlopen(link.group(1))
                html = c.read()
                c.close()
                title = TITLE_RE.search(html)
                if title: title = title.group(1)
                else: title = link.group(2)

                cache.set(key, title, 86400)

            links[link.group(1)] = cache.get(key)

        return links
    links = property(_get_article_links)

    def get_absolute_url(self):
        return reverse('articles_display_article', args=[self.publish_date.year, self.slug])

    def _get_teaser(self):
        if len(self.description.strip()):
            text = self.description
        else:
            text = self.rendered_content

        words = text.split(' ')
        if len(words) > WORD_LIMIT:
            text = '%s...' % ' '.join(words[:WORD_LIMIT])
        return text
    teaser = property(_get_teaser)

    class Meta:
        ordering = ('-publish_date', 'title')
