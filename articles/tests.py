from django.contrib.auth.models import User
from django.test import TestCase

from models import Article, ArticleStatus, Tag

class ArticleTestCase(TestCase):
    fixtures = ['users']

    def setUp(self):
        self.superuser = User.objects.filter(is_superuser=True)[0]

    def new_article(self, title, content, tags=[], **kwargs):
        a = Article(
            title=title,
            content=content,
            author=self.superuser,
            **kwargs
        )
        a.save()

        if tags:
            a.tags = tags
            a.save()

        return a

    def test_unique_slug(self):
        """Unique slugs"""

        a1 = self.new_article('Same Slug', 'Some content')
        a2 = self.new_article('Same Slug', 'Some more content')

        self.assertNotEqual(a1.slug, a2.slug)

    def test_active_articles(self):
        """Active articles"""

        a1 = self.new_article('New Article', 'This is a new article')
        a2 = self.new_article('New Article', 'This is a new article', is_active=False)

        self.assertEquals(len(Article.objects.active()), 1)

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

        self.assertEqual(len(t.article_set.live()), 1)
        self.assertEqual(len(t.article_set.active()), 2)

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

        self.assertEquals(len(Article.objects.live()), 2)
        self.assertEquals(len(Article.objects.live(self.superuser)), 3)

