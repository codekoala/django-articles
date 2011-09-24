from base64 import encodestring
from datetime import datetime
import logging
import mimetypes
import re
import urllib

from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.markup.templatetags import markup
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.conf import settings
from django.template.defaultfilters import slugify, striptags
from django.utils.translation import ugettext_lazy as _

from decorators import logtime, once_per_instance

WORD_LIMIT = getattr(settings, 'ARTICLES_TEASER_LIMIT', 75)
AUTO_TAG = getattr(settings, 'ARTICLES_AUTO_TAG', True)
DEFAULT_DB = getattr(settings, 'ARTICLES_DEFAULT_DB', 'default')
LOOKUP_LINK_TITLE = getattr(settings, 'ARTICLES_LOOKUP_LINK_TITLE', True)

MARKUP_HTML = 'h'
MARKUP_MARKDOWN = 'm'
MARKUP_REST = 'r'
MARKUP_TEXTILE = 't'
MARKUP_OPTIONS = getattr(settings, 'ARTICLE_MARKUP_OPTIONS', (
        (MARKUP_HTML, _('HTML/Plain Text')),
        (MARKUP_MARKDOWN, _('Markdown')),
        (MARKUP_REST, _('ReStructured Text')),
        (MARKUP_TEXTILE, _('Textile'))
    ))
MARKUP_DEFAULT = getattr(settings, 'ARTICLE_MARKUP_DEFAULT', MARKUP_HTML)

USE_ADDTHIS_BUTTON = getattr(settings, 'USE_ADDTHIS_BUTTON', True)
ADDTHIS_USE_AUTHOR = getattr(settings, 'ADDTHIS_USE_AUTHOR', True)
DEFAULT_ADDTHIS_USER = getattr(settings, 'DEFAULT_ADDTHIS_USER', None)

# regex used to find links in an article
LINK_RE = re.compile('<a.*?href="(.*?)".*?>(.*?)</a>', re.I|re.M)
TITLE_RE = re.compile('<title.*?>(.*?)</title>', re.I|re.M)
TAG_RE = re.compile('[^a-z0-9\-_\+\:\.]?', re.I)

log = logging.getLogger('articles.models')

def get_name(user):
    """
    Provides a way to fall back to a user's username if their full name has not
    been entered.
    """

    key = 'username_for_%s' % user.id

    log.debug('Looking for "%s" in cache (%s)' % (key, user))
    name = cache.get(key)
    if not name:
        log.debug('Name not found')

        if len(user.get_full_name().strip()):
            log.debug('Using full name')
            name = user.get_full_name()
        else:
            log.debug('Using username')
            name = user.username

        log.debug('Caching %s as "%s" for a while' % (key, name))
        cache.set(key, name, 86400)

    return name
User.get_name = get_name

class Tag(models.Model):
    name = models.CharField(max_length=64, unique=True)
    slug = models.CharField(max_length=64, unique=True, null=True, blank=True)

    def __unicode__(self):
        return self.name

    @staticmethod
    def clean_tag(name):
        """Replace spaces with dashes, in case someone adds such a tag manually"""

        name = name.replace(' ', '-').encode('ascii', 'ignore')
        name = TAG_RE.sub('', name)
        clean = name.lower().strip()

        log.debug('Cleaned tag "%s" to "%s"' % (name, clean))
        return clean

    def save(self, *args, **kwargs):
        """Cleans up any characters I don't want in a URL"""

        log.debug('Ensuring that tag "%s" has a slug' % (self,))
        self.slug = Tag.clean_tag(self.name)
        super(Tag, self).save(*args, **kwargs)

    @models.permalink
    def get_absolute_url(self):
        return ('articles_display_tag', (self.cleaned,))

    @property
    def cleaned(self):
        """Returns the clean version of the tag"""

        return self.slug or Tag.clean_tag(self.name)

    @property
    def rss_name(self):
        return self.cleaned

    class Meta:
        ordering = ('name',)

class ArticleStatusManager(models.Manager):

    def default(self):
        default = self.all()[:1]

        if len(default) == 0:
            return None
        else:
            return default[0]

class ArticleStatus(models.Model):
    name = models.CharField(max_length=50)
    ordering = models.IntegerField(default=0)
    is_live = models.BooleanField(default=False, blank=True)

    objects = ArticleStatusManager()

    class Meta:
        ordering = ('ordering', 'name')
        verbose_name_plural = _('Article statuses')

    def __unicode__(self):
        if self.is_live:
            return u'%s (live)' % self.name
        else:
            return self.name

class ArticleManager(models.Manager):

    def active(self):
        """
        Retrieves all active articles which have been published and have not
        yet expired.
        """
        now = datetime.now()
        return self.get_query_set().filter(
                Q(expiration_date__isnull=True) |
                Q(expiration_date__gte=now),
                publish_date__lte=now,
                is_active=True)

    def live(self, user=None):
        """Retrieves all live articles"""

        qs = self.active()

        if user is not None and user.is_superuser:
            # superusers get to see all articles
            return qs
        else:
            # only show live articles to regular users
            return qs.filter(status__is_live=True)

MARKUP_HELP = _("""Select the type of markup you are using in this article.
<ul>
<li><a href="http://daringfireball.net/projects/markdown/basics" target="_blank">Markdown Guide</a></li>
<li><a href="http://docutils.sourceforge.net/docs/user/rst/quickref.html" target="_blank">ReStructured Text Guide</a></li>
<li><a href="http://thresholdstate.com/articles/4312/the-textile-reference-manual" target="_blank">Textile Guide</a></li>
</ul>""")

class Article(models.Model):
    title = models.CharField(max_length=100)
    slug = models.SlugField(unique_for_year='publish_date')
    status = models.ForeignKey(ArticleStatus, default=ArticleStatus.objects.default)
    author = models.ForeignKey(User)
    sites = models.ManyToManyField(Site, blank=True)

    keywords = models.TextField(blank=True, help_text=_("If omitted, the keywords will be the same as the article tags."))
    description = models.TextField(blank=True, help_text=_("If omitted, the description will be determined by the first bit of the article's content."))

    markup = models.CharField(max_length=1, choices=MARKUP_OPTIONS, default=MARKUP_DEFAULT, help_text=MARKUP_HELP)
    content = models.TextField()
    rendered_content = models.TextField()

    tags = models.ManyToManyField(Tag, help_text=_('Tags that describe this article'), blank=True)
    auto_tag = models.BooleanField(default=AUTO_TAG, blank=True, help_text=_('Check this if you want to automatically assign any existing tags to this article based on its content.'))
    followup_for = models.ManyToManyField('self', symmetrical=False, blank=True, help_text=_('Select any other articles that this article follows up on.'), related_name='followups')
    related_articles = models.ManyToManyField('self', blank=True)

    publish_date = models.DateTimeField(default=datetime.now, help_text=_('The date and time this article shall appear online.'))
    expiration_date = models.DateTimeField(blank=True, null=True, help_text=_('Leave blank if the article does not expire.'))

    is_active = models.BooleanField(default=True, blank=True)
    login_required = models.BooleanField(blank=True, help_text=_('Enable this if users must login before they can read this article.'))

    use_addthis_button = models.BooleanField(_('Show AddThis button'), blank=True, default=USE_ADDTHIS_BUTTON, help_text=_('Check this to show an AddThis bookmark button when viewing an article.'))
    addthis_use_author = models.BooleanField(_("Use article author's username"), blank=True, default=ADDTHIS_USE_AUTHOR, help_text=_("Check this if you want to use the article author's username for the AddThis button.  Respected only if the username field is left empty."))
    addthis_username = models.CharField(_('AddThis Username'), max_length=50, blank=True, default=DEFAULT_ADDTHIS_USER, help_text=_('The AddThis username to use for the button.'))

    objects = ArticleManager()

    def __init__(self, *args, **kwargs):
        """Makes sure that we have some rendered content to use"""

        super(Article, self).__init__(*args, **kwargs)

        self._next = None
        self._previous = None
        self._teaser = None

        if self.id:
            # mark the article as inactive if it's expired and still active
            if self.expiration_date and self.expiration_date <= datetime.now() and self.is_active:
                self.is_active = False
                self.save()

            if not self.rendered_content or not len(self.rendered_content.strip()):
                self.save()

    def __unicode__(self):
        return self.title

    def save(self, *args, **kwargs):
        """Renders the article using the appropriate markup language."""

        using = kwargs.get('using', DEFAULT_DB)

        self.do_render_markup()
        self.do_addthis_button()
        self.do_meta_description()
        self.do_unique_slug(using)

        super(Article, self).save(*args, **kwargs)

        # do some things that require an ID first
        requires_save = self.do_auto_tag(using)
        requires_save |= self.do_tags_to_keywords()
        requires_save |= self.do_default_site(using)

        if requires_save:
            # bypass the other processing
            super(Article, self).save()

    def do_render_markup(self):
        """Turns any markup into HTML"""

        original = self.rendered_content
        if self.markup == MARKUP_MARKDOWN:
            self.rendered_content = markup.markdown(self.content)
        elif self.markup == MARKUP_REST:
            self.rendered_content = markup.restructuredtext(self.content)
        elif self.markup == MARKUP_TEXTILE:
            self.rendered_content = markup.textile(self.content)
        else:
            self.rendered_content = self.content

        return (self.rendered_content != original)

    def do_addthis_button(self):
        """Sets the AddThis username for this post"""

        # if the author wishes to have an "AddThis" button on this article,
        # make sure we have a username to go along with it.
        if self.use_addthis_button and self.addthis_use_author and not self.addthis_username:
            self.addthis_username = self.author.username
            return True

        return False

    def do_unique_slug(self, using=DEFAULT_DB):
        """
        Ensures that the slug is always unique for the year this article was
        posted
        """

        if not self.id:
            # make sure we have a slug first
            if not len(self.slug.strip()):
                self.slug = slugify(self.title)

            self.slug = self.get_unique_slug(self.slug, using)
            return True

        return False

    def do_tags_to_keywords(self):
        """
        If meta keywords is empty, sets them using the article tags.

        Returns True if an additional save is required, False otherwise.
        """

        if len(self.keywords.strip()) == 0:
            self.keywords = ', '.join([t.name for t in self.tags.all()])
            return True

        return False

    def do_meta_description(self):
        """
        If meta description is empty, sets it to the article's teaser.

        Returns True if an additional save is required, False otherwise.
        """

        if len(self.description.strip()) == 0:
            self.description = self.teaser
            return True

        return False

    @logtime
    @once_per_instance
    def do_auto_tag(self, using=DEFAULT_DB):
        """
        Performs the auto-tagging work if necessary.

        Returns True if an additional save is required, False otherwise.
        """

        if not self.auto_tag:
            log.debug('Article "%s" (ID: %s) is not marked for auto-tagging. Skipping.' % (self.title, self.pk))
            return False

        # don't clobber any existing tags!
        existing_ids = [t.id for t in self.tags.all()]
        log.debug('Article %s already has these tags: %s' % (self.pk, existing_ids))

        unused = Tag.objects.all()
        if hasattr(unused, 'using'):
            unused = unused.using(using)
        unused = unused.exclude(id__in=existing_ids)

        found = False
        to_search = (self.content, self.title, self.description, self.keywords)
        for tag in unused:
            regex = re.compile(r'\b%s\b' % tag.name, re.I)
            if any(regex.search(text) for text in to_search):
                log.debug('Applying Tag "%s" (%s) to Article %s' % (tag, tag.pk, self.pk))
                self.tags.add(tag)
                found = True

        return found

    def do_default_site(self, using=DEFAULT_DB):
        """
        If no site was selected, selects the site used to create the article
        as the default site.

        Returns True if an additional save is required, False otherwise.
        """

        if not len(self.sites.all()):
            sites = Site.objects.all()
            if hasattr(sites, 'using'):
                sites = sites.using(using)
            self.sites.add(sites.get(pk=settings.SITE_ID))
            return True

        return False

    def get_unique_slug(self, slug, using=DEFAULT_DB):
        """Iterates until a unique slug is found"""

        # we need a publish date before we can do anything meaningful
        if type(self.publish_date) is not datetime:
            return slug

        orig_slug = slug
        year = self.publish_date.year
        counter = 1

        while True:
            not_unique = Article.objects.all()
            if hasattr(not_unique, 'using'):
                not_unique = not_unique.using(using)
            not_unique = not_unique.filter(publish_date__year=year, slug=slug)

            if len(not_unique) == 0:
                return slug

            slug = '%s-%s' % (orig_slug, counter)
            counter += 1

    def _get_article_links(self):
        """
        Find all links in this article.  When a link is encountered in the
        article text, this will attempt to discover the title of the page it
        links to.  If there is a problem with the target page, or there is no
        title (ie it's an image or other binary file), the text of the link is
        used as the title.  Once a title is determined, it is cached for a week
        before it will be requested again.
        """

        links = []

        # find all links in the article
        log.debug('Locating links in article: %s' % (self,))
        for link in LINK_RE.finditer(self.rendered_content):
            url = link.group(1)
            log.debug('Do we have a title for "%s"?' % (url,))
            key = 'href_title_' + encodestring(url).strip()

            # look in the cache for the link target's title
            title = cache.get(key)
            if title is None:
                log.debug('Nope... Getting it and caching it.')
                title = link.group(2)

                if LOOKUP_LINK_TITLE:
                    try:
                        log.debug('Looking up title for URL: %s' % (url,))
                        # open the URL
                        c = urllib.urlopen(url)
                        html = c.read()
                        c.close()

                        # try to determine the title of the target
                        title_m = TITLE_RE.search(html)
                        if title_m:
                            title = title_m.group(1)
                            log.debug('Found title: %s' % (title,))
                    except:
                        # if anything goes wrong (ie IOError), use the link's text
                        log.warn('Failed to retrieve the title for "%s"; using link text "%s"' % (url, title))

                # cache the page title for a week
                log.debug('Using "%s" as title for "%s"' % (title, url))
                cache.set(key, title, 604800)

            # add it to the list of links and titles
            if url not in (l[0] for l in links):
                links.append((url, title))

        return tuple(links)
    links = property(_get_article_links)

    def _get_word_count(self):
        """Stupid word counter for an article."""

        return len(striptags(self.rendered_content).split(' '))
    word_count = property(_get_word_count)

    @models.permalink
    def get_absolute_url(self):
        return ('articles_display_article', (self.publish_date.year, self.slug))

    def _get_teaser(self):
        """
        Retrieve some part of the article or the article's description.
        """
        if not self._teaser:
            if len(self.description.strip()):
                text = self.description
            else:
                text = self.rendered_content

            words = text.split(' ')
            if len(words) > WORD_LIMIT:
                text = '%s...' % ' '.join(words[:WORD_LIMIT])
            self._teaser = text

        return self._teaser
    teaser = property(_get_teaser)

    def get_next_article(self):
        """Determines the next live article"""

        if not self._next:
            try:
                qs = Article.objects.live().exclude(id__exact=self.id)
                article = qs.filter(publish_date__gte=self.publish_date).order_by('publish_date')[0]
            except (Article.DoesNotExist, IndexError):
                article = None
            self._next = article

        return self._next

    def get_previous_article(self):
        """Determines the previous live article"""

        if not self._previous:
            try:
                qs = Article.objects.live().exclude(id__exact=self.id)
                article = qs.filter(publish_date__lte=self.publish_date).order_by('-publish_date')[0]
            except (Article.DoesNotExist, IndexError):
                article = None
            self._previous = article

        return self._previous

    class Meta:
        ordering = ('-publish_date', 'title')
        get_latest_by = 'publish_date'

class Attachment(models.Model):
    upload_to = lambda inst, fn: 'attach/%s/%s/%s' % (datetime.now().year, inst.article.slug, fn)

    article = models.ForeignKey(Article, related_name='attachments')
    attachment = models.FileField(upload_to=upload_to)
    caption = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ('-article', 'id')

    def __unicode__(self):
        return u'%s: %s' % (self.article, self.caption)

    @property
    def filename(self):
        return self.attachment.name.split('/')[-1]

    @property
    def content_type_class(self):
        mt = mimetypes.guess_type(self.attachment.path)[0]
        if mt:
            content_type = mt.replace('/', '_')
        else:
            # assume everything else is text/plain
            content_type = 'text_plain'

        return content_type

