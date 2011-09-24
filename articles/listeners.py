import logging

from django.db.models import signals, Q

from decorators import logtime
from models import Article, Tag

log = logging.getLogger('articles.listeners')

@logtime
def apply_new_tag(sender, instance, created, using='default', **kwargs):
    """Applies new tags to existing articles that are marked for auto-tagging"""

    # attempt to find all articles that contain the new tag
    # TODO: make sure this is standard enough... seems that both MySQL and
    # PostgreSQL support it...
    tag = r'[[:<:]]%s[[:>:]]' % instance.name

    log.debug('Searching for auto-tag Articles using regex: %s' % (tag,))
    applicable_articles = Article.objects.filter(
        Q(auto_tag=True),
        Q(content__iregex=tag) |
        Q(title__iregex=tag) |
        Q(description__iregex=tag) |
        Q(keywords__iregex=tag)
    )

    log.debug('Found %s matches' % len(applicable_articles))
    for article in applicable_articles:
        log.debug('Applying Tag "%s" (%s) to Article "%s" (%s)' % (instance, instance.pk, article.title, article.pk))
        article.tags.add(instance)
        article.save()

signals.post_save.connect(apply_new_tag, sender=Tag)
