from django.core.management.base import NoArgsCommand
from articles.models import Article, Tag

class Command(NoArgsCommand):
    help = """Converts our old categories into tags"""

    def handle_noargs(self, **opts):
        from django.db import connection

        c = connection.cursor()

        for article in Article.objects.all():
            c.execute("""SELECT c.slug
FROM articles_article_categories aac
JOIN articles_category c
ON aac.category_id = c.id
WHERE aac.article_id=%s""", (article.id,))

            names = [row[0] for row in c.fetchall()]
            tags = [Tag.objects.get_or_create(name=t)[0] for t in names]
            article.tags = tags
            article.save()

