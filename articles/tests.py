# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from django.contrib.auth.models import User, Permission
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client

from models import Article, ArticleStatus, Tag, get_name, MARKUP_HTML, MARKUP_MARKDOWN, MARKUP_REST, MARKUP_TEXTILE

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

    def test_tag_save(self):
        """Makes sure the overridden save method works for Tags"""

        t = Tag.objects.create(name='wasabi')
        t.name = 'DERP'
        t.save()

        self.assertEqual(t.slug, 'derp')

    def test_get_absolute_url(self):
        name = 'Hi There'
        t = Tag.objects.create(name=name)
        self.assertEqual(t.get_absolute_url(), reverse('articles_display_tag', args=[Tag.clean_tag(name)]))

class ArticleStatusTestCase(TestCase):

    def setUp(self):
        pass

    def test_instantiation(self):
        _as = ArticleStatus(name='Fake', ordering=5, is_live=True)
        self.assertEqual(unicode(_as), u'Fake (live)')

        _as.is_live = False
        self.assertEqual(unicode(_as), u'Fake')

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

    def test_auto_expire(self):
        """
        Makes sure that articles set to expire will actually be marked inactive
        """

        one_second_ago = datetime.now() - timedelta(seconds=1)
        a = self.new_article('Expiring Article', 'I expired one second ago', is_active=True, expiration_date=one_second_ago)

        self.assertTrue(a.is_active)

        b = Article.objects.latest()
        self.assertFalse(b.is_active)

    def test_markup_markdown(self):
        """Makes sure markdown works"""

        a = self.new_article('Demo', '''A First Level Header
====================

A Second Level Header
---------------------

Now is the time for all good men to come to
the aid of their country. This is just a
regular paragraph.''', markup=MARKUP_MARKDOWN)
        a.do_render_markup()

        print a.rendered_content

    def test_markup_rest(self):
        """Makes sure reStructuredText works"""

        a = self.new_article('Demo', '''A First Level Header
====================

A Second Level Header
---------------------

Now is the time for all good men to come to
the aid of their country. This is just a
regular paragraph.''', markup=MARKUP_REST)
        a.do_render_markup()

        print a.rendered_content

    def test_markup_textile(self):
        """Makes sure textile works"""

        a = self.new_article('Demo', '''A First Level Header
====================

A Second Level Header
---------------------

Now is the time for all good men to come to
the aid of their country. This is just a
regular paragraph.''', markup=MARKUP_TEXTILE)
        a.do_render_markup()

        print a.rendered_content

    def test_markup_html(self):
        """Makes sure HTML works (derp)"""

        html = '''<h1>A First Level Header</h1>
<h2>A Second Level Header</h2>

<p>Now is the time for all good men to come to
the aid of their country. This is just a
regular paragraph.</p>'''

        a = self.new_article('Demo', html, markup=MARKUP_HTML)
        a.do_render_markup()
        self.assertEqual(html, a.rendered_content)

class ArticleAdminTestCase(TestCase, ArticleUtilMixin):
    fixtures = ['users']

    def setUp(self):
        self.client = Client()

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
            '_selected_action': Article.objects.all().values_list('id', flat=True)[0:3],
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
            '_selected_action': Article.objects.all().values_list('id', flat=True)[0:3],
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
            '_selected_action': Article.objects.all().values_list('id', flat=True),
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
            'tags': 'this is a test',
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

class FeedTestCase(TestCase, ArticleUtilMixin):
    fixtures = ['tags', 'users']

    def setUp(self):
        self.client = Client()

        status = ArticleStatus.objects.filter(is_live=True)[0]
        self.new_article('This is a test!', 'Testing testing 1 2 3',
                         tags=Tag.objects.all(), status=status)

    def test_latest_entries(self):
        """Makes sure the latest entries feed works"""

        res = self.client.get(reverse('articles_rss_feed_latest'))
        self.assertEqual(res.status_code, 200)

        res = self.client.get(reverse('articles_atom_feed_latest'))
        self.assertEqual(res.status_code, 200)

    def test_tags(self):
        """Makes sure that the tags feed works"""

        res = self.client.get(reverse('articles_rss_feed_tag', args=['demo']))
        self.assertEqual(res.status_code, 200)

        res = self.client.get(reverse('articles_rss_feed_tag', args=['demox']))
        self.assertEqual(res.status_code, 404)

        res = self.client.get(reverse('articles_atom_feed_tag', args=['demo']))
        self.assertEqual(res.status_code, 200)

        res = self.client.get(reverse('articles_atom_feed_tag', args=['demox']))
        self.assertEqual(res.status_code, 404)

class FormTestCase(TestCase, ArticleUtilMixin):
    fixtures = ['users',]

    def setUp(self):
        self.client = Client()

        User.objects.create_superuser('admin', 'admin@admin.com', 'admin')
        self.client.login(username='admin', password='admin')

    def tearDown(self):
        pass

    def test_article_admin_form(self):
        """Makes sure the ArticleAdminForm works as expected"""

        a = self.new_article('Sample', 'sample')
        res = self.client.get(reverse('admin:articles_article_change', args=[a.id]))
        self.assertEqual(res.status_code, 200)

class ListenerTestCase(TestCase, ArticleUtilMixin):
    fixtures = ['users', 'tags']

    def test_apply_new_tag(self):
        """Makes sure auto-tagging works"""

        a = self.new_article('Yay', 'This is just a demonstration of how awesome Django and Python are.', auto_tag=True)
        self.assertEqual(a.tags.count(), 0)

        Tag.objects.create(name='awesome')
        Tag.objects.create(name='Python')
        t = Tag.objects.create(name='Django')

        # make sure the tags were actually applied to our new article
        self.assertEqual(a.tags.count(), 3)

class MiscTestCase(TestCase):
    fixtures = ['users',]

    def test_get_name(self):
        u1 = User.objects.get(pk=1)
        u2 = User.objects.get(pk=2)

        self.assertEqual(get_name(u1), 'superuser')
        self.assertEqual(get_name(u2), 'Jim Bob')

        self.assertEqual(u1.get_name(), 'superuser')
        self.assertEqual(u2.get_name(), 'Jim Bob')
