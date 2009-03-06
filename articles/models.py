from django.db import models, connection
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.contrib.sitemaps import ping_google
from django.contrib.markup.templatetags.markup import restructuredtext
from django.core.urlresolvers import reverse
from django.conf import settings
from datetime import datetime
import commands
import os
import re
import xmlrpclib
import unicodedata

WORD_LIMIT = getattr(settings, 'ARTICLES_TEASER_LIMIT', 75)

class CategoryManager(models.Manager):
    def active(self):
        return self.get_query_set().filter(is_active=True)

class Category(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField()
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
    slug = models.SlugField(unique_for_date='publish_date')
    keywords = models.TextField(blank=True)
    description = models.TextField(blank=True, help_text="If omitted, the description will be determined by the first bit of the article's content.")
    author = models.ForeignKey(User)
    content = models.TextField()
    rendered_content = models.TextField()
    categories = models.ManyToManyField(Category, help_text='Select any categories to classify this article.', blank=True)
    followup_for = models.ManyToManyField('self', symmetrical=False, blank=True, help_text='Select any other articles that this article follows up on.', related_name='followups')
    related_articles = models.ManyToManyField('self', blank=True)
    is_active = models.BooleanField(default=True, blank=True)
    is_commentable = models.BooleanField(default=True, blank=True)
    make_pdf = models.BooleanField(default=True, blank=True)
    publish_date = models.DateTimeField(default=datetime.now)
    expiration_date = models.DateTimeField(blank=True, null=True)

    objects = ArticleManager()

    def __init__(self, *args, **kwargs):
        super(Article, self).__init__(*args, **kwargs)

        if self.id:
            if not self.rendered_content or not len(self.rendered_content):
                self.save()

    def __unicode__(self):
        return self.title

    def save(self):
        # make sure each article has a heading
        if not self.content.startswith('==='):
            line = '=' * len(self.title)
            self.content = """%s
%s
%s

:author: Josh VanderLinden <codekoala@gmail.com>
:date: %s
:Homepage: http://www.codekoala.com/

%s
""" % (line, self.title, line,
       self.publish_date.strftime('%d %b %Y'), self.content)

        # no more page breaks please
        self.content = self.content.replace(PAGE_BREAK, '')

        # let's use "code-block" instead of "sourcecode" for the PDFs
        self.content = self.content.replace('.. sourcecode:: ',
                                            '.. code-block:: ')

        self.rendered_content = restructuredtext(self.content)
        super(Article, self).save()

        # don't save any .rst or .pdf files if we're in debug mode or it's
        # specifically checked
        #if settings.DEBUG or not self.make_pdf: return

        # create a PDF version of the article
        out_dir = os.path.join(settings.MEDIA_ROOT, 'articles')
        rst_dir = os.path.join(out_dir, 'rst')
        pdf_dir = os.path.join(out_dir, 'pdfs')

        # ensure that the RST directory exists
        try: os.makedirs(rst_dir)
        except OSError: pass

        # ensure that the PDF directory exists
        try: os.makedirs(pdf_dir)
        except OSError: pass

        # save the RST
        pdf_file = os.path.join(pdf_dir, self.slug + '.pdf')
        rst_file = os.path.join(rst_dir, self.slug + '.rst')

        real_content = clean_content = u_clean(self.content)

        # now clean it up a bit more for the PDF
        #clean_content = clean_content.replace('    :linenos:\r\n', '    :linenos: true\r\n')
        clean_content = re.sub('(:(H|h)omepage:.*\n)',
                                r'\1:URL: http://www.codekoala.com%s\n\n .. header::\n\n    Copyright (c) %i Josh VanderLinden\n\n .. footer::\n\n    page ###Page###\n' % (self.get_absolute_url(), self.publish_date.year), clean_content)
        clean_content = re.sub('( .. image:: http://www.codekoala.com/static/)',
                              r' .. image:: %s/' % settings.MEDIA_ROOT,
                              clean_content)

        # see if we have any comments on this article
        content_type = ContentType.objects.get_for_model(Article)
        comments = Comment.objects.filter(content_type=content_type, object_pk=str(self.id))
        if comments.count():
            # we do, so tack on the comments for the PDF
            clean_content += '\n\nComments\n========\n\n'
            for comment in comments:
                clean_content += """%s said...\n%s

%s

Posted: %s

""" % (u_clean(comment.name),
        '-' * len(comment.name + ' said...'),
        u_clean(comment.comment),
        comment.submit_date)

        #print clean_content
        self.__save_pdf(rst_file, pdf_file, clean_content)

        # try to access the PDF file.  If it's there, we can assume that all
        # went well.  If it's not there, try removing the :linenos: option
        if not os.access(pdf_file, os.R_OK):
            clean_content = clean_content.replace('    :linenos:\r\n', '')
            self.__save_pdf(rst_file, pdf_file, clean_content)

        # now save the "real" RST
        rst = open(rst_file, 'w')
        rst.write(real_content)
        rst.close()

        if not settings.DEBUG:
            # try to tell google that we have a new article
            try:
                ping_google()
            except Exception:
                pass

    def __save_pdf(self, rst_file, pdf_file, content):
        """
        Attempts to save a PDF version of the article.
        """

        # save the PDF-appropriate RST
        rst = open(rst_file, 'w')
        rst.write(u_clean(content))
        rst.close()

        # generate the PDF
        commands.getoutput('rst2pdf %s -o %s' % (rst_file, pdf_file))

    def get_absolute_url(self):
        info = self.publish_date.strftime('%Y/%b/%d').lower().split('/') + [self.slug]
        return reverse('articles_display_article', args=info)

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

    def next_article(self):
        try:
            article = Article.objects.active().exclude(id__exact=self.id).filter(publish_date__gte=self.publish_date).order_by('publish_date')[0]
        except (Article.DoesNotExist, IndexError):
            article = None
        return article

    def previous_article(self):
        try:
            article = Article.objects.active().exclude(id__exact=self.id).filter(publish_date__lte=self.publish_date).order_by('-publish_date')[0]
        except (Article.DoesNotExist, IndexError):
            article = None
        return article

    class Meta:
        ordering = ('-publish_date', 'title')

# wrap the save comment method so the PDF will be regenerated as soon as a new
# comment is posted
def update_pdf(func):
    def new(obj, *args, **kwargs):
        result = func(obj, *args, **kwargs)

        # only save the object whose comment was just saved if it's an Article
        if isinstance(obj.content_object, Article):
            obj.content_object.save()

        return result
    return new

Comment.save = update_pdf(Comment.save)

def u_clean(s):
    """
    Cleans up dirty unicode text.
    """
    uni = ''
    try:
        # try this first
        uni = str(s).decode('iso-8859-1')
    except:
        try:
            # try utf-8 next
            uni = str(s).decode('utf-8')
        except:
            # last resort method... one character at a time
            if s and type(s) in (str, unicode):
                for c in s:
                    try:
                        uni += unicodedata.normalize('NFKC', unicode(c))
                    except:
                        uni += '-'

    return uni.encode('ascii', 'xmlcharrefreplace')
