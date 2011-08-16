# -*- coding: utf-8 -*-

from django.contrib.auth.models import User, Permission
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client, RequestFactory

from models import Article, ArticleStatus, Tag, MARKUP_HTML

class ArticleUtilMixin(object):

    @property
    def superuser(self):
        if not hasattr(self, '_superuser'):
            self._superuser = User.objects.filter(is_superuser=True)[0]

        return self._superuser

    def new_article(self, title, content, tags=[], author=None, **kwargs):
        a = Article(
            title=title,
            content=content,
            author=author or self.superuser,
            **kwargs
        )
        a.save()

        if tags:
            a.tags = tags
            a.save()

        return a

class TagTestCase(TestCase):
    fixtures = ['tags']

    def setUp(self):
        self.client = Client()

    def test_unicode_tag(self):
        """Unicode characters in tags (issue #10)"""

        name = u'Căutare avansată'
        t = Tag.objects.create(name=name)
        self.assertEqual(t.slug, 'cutare-avansat')

        response = self.client.get(t.get_absolute_url())
        self.assertEqual(response.status_code, 200)

        # make sure older tags still work
        t2 = Tag.objects.get(pk=2)
        response = self.client.get(t2.get_absolute_url())
        self.assertEqual(response.status_code, 200)

class ArticleTestCase(TestCase, ArticleUtilMixin):
    fixtures = ['users']

    def setUp(self):
        pass

    def test_unique_slug(self):
        """Unique slugs"""

        a1 = self.new_article('Same Slug', 'Some content')
        a2 = self.new_article('Same Slug', 'Some more content')

        self.assertNotEqual(a1.slug, a2.slug)

    def test_active_articles(self):
        """Active articles"""

        a1 = self.new_article('New Article', 'This is a new article')
        a2 = self.new_article('New Article', 'This is a new article', is_active=False)

        self.assertEquals(Article.objects.active().count(), 1)

    def test_default_status(self):
        """Default status selection"""

        default_status = ArticleStatus.objects.default()
        other_status = ArticleStatus.objects.exclude(id=default_status.id)[0]

        self.assertTrue(default_status.ordering < other_status.ordering)

    def test_tagged_article_status(self):
        """Tagged article status"""

        t = Tag.objects.create(name='Django')

        draft = ArticleStatus.objects.filter(is_live=False)[0]
        finished = ArticleStatus.objects.filter(is_live=True)[0]

        a1 = self.new_article('Tagged', 'draft', status=draft, tags=[t])
        a2 = self.new_article('Tagged', 'finished', status=finished, tags=[t])

        self.assertEqual(t.article_set.live().count(), 1)
        self.assertEqual(t.article_set.active().count(), 2)

    def test_new_article_status(self):
        """New article status is default"""

        default_status = ArticleStatus.objects.default()
        article = self.new_article('New Article', 'This is a new article')
        self.failUnless(article.status == default_status)

    def test_live_articles(self):
        """Only live articles"""

        live_status = ArticleStatus.objects.filter(is_live=True)[0]
        a1 = self.new_article('New Article', 'This is a new article')
        a2 = self.new_article('New Article', 'This is a new article', is_active=False)
        a3 = self.new_article('New Article', 'This is a new article', status=live_status)
        a4 = self.new_article('New Article', 'This is a new article', status=live_status)

        self.assertEquals(Article.objects.live().count(), 2)
        self.assertEquals(Article.objects.live(self.superuser).count(), 3)

class ArticleAdminTest(TestCase, ArticleUtilMixin):
    fixtures = ['users']

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

        User.objects.create_superuser('admin', 'admin@admin.com', 'admin')
        self.client.login(username='admin', password='admin')

    def tearDown(self):
        pass

    def test_mark_active(self):
        """Creates some inactive articles and marks them active"""

        for i in range(5):
            self.new_article('Article %s' % (i,), 'Content for article %s' % (i,), is_active=False)

        # check number of active articles
        self.assertEqual(Article.objects.active().count(), 0)

        # mark some articles active
        self.client.post(reverse('admin:articles_article_changelist'), {
            '_selected_action': ['1','2','3'],
            'index': 0,
            'action': 'mark_active',
        })

        # check number of active articles
        self.assertEqual(Article.objects.active().count(), 3)

    def test_mark_inactive(self):
        """Creates some active articles and marks them inactive"""

        for i in range(5):
            self.new_article('Article %s' % (i,), 'Content for article %s' % (i,))

        # check number of active articles
        self.assertEqual(Article.objects.active().count(), 5)

        # mark some articles inactive
        self.client.post(reverse('admin:articles_article_changelist'), {
            '_selected_action': ['1','2','3'],
            'index': 0,
            'action': 'mark_inactive',
        })

        # check number of active articles
        self.assertEqual(Article.objects.active().count(), 2)

    def test_dynamic_status(self):
        """Sets the status for multiple articles to something dynamic"""

        default_status = ArticleStatus.objects.default()
        other_status = ArticleStatus.objects.exclude(id=default_status.id)[0]

        self.new_article('An Article', 'Some content')
        self.new_article('Another Article', 'Some content')

        # make sure we have articles with the default status
        self.assertEqual(Article.objects.filter(status=default_status).count(), 2)

        # mark them with the other status
        self.client.post(reverse('admin:articles_article_changelist'), {
            '_selected_action': ['1','2'],
            'index': 0,
            'action': 'mark_status_%s' % (other_status.id,),
        })

        # make sure we have articles with the other status
        self.assertEqual(Article.objects.filter(status=other_status).count(), 2)

    def test_automatic_author(self):
        """
        Makes sure the author of an article will be set automatically based on
        the user who is logged in
        """

        res = self.client.post(reverse('admin:articles_article_add'), {
            'title': 'A new article',
            'slug': 'new-article',
            'content': 'Some content',
            'status': ArticleStatus.objects.default().id,
            'markup': MARKUP_HTML,
            'publish_date_0': '2011-08-15',
            'publish_date_1': '09:00:00',
            'attachments-TOTAL_FORMS': 5,
            'attachments-INITIAL_FORMS': 0,
            'attachments-MAX_NUM_FORMS': 15,
        })

        self.assertRedirects(res, reverse('admin:articles_article_changelist'))
        self.assertEqual(Article.objects.filter(author__username='admin').count(), 1)

    def test_non_superuser(self):
        """Makes sure that non-superuser users can only see articles they posted"""

        # add some articles as the superuser
        for i in range(5):
            self.new_article('This is a test', 'with some content')

        # now add some as a non-superuser
        joe = User.objects.create_user('joe', 'joe@bob.com', 'bob')
        joe.is_staff = True
        joe.user_permissions = Permission.objects.filter(codename__endswith='_article')
        joe.save()

        self.client.login(username='joe', password='bob')
        for i in range(5):
            self.new_article('I am not a super user', 'har har', author=joe)

        # display all articles that the non-superuser can see
        res = self.client.get(reverse('admin:articles_article_changelist'))
        self.assertEqual(res.content.count('_selected_action'), 5)

        # make sure the superuser can see all of them
        self.client.login(username='admin', password='admin')
        res = self.client.get(reverse('admin:articles_article_changelist'))
        self.assertEqual(res.content.count('_selected_action'), 10)
