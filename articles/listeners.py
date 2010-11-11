from django.db.models import signals
from models import Article, Tag

def article_post_processing(sender, instance, created, **kwargs):
    """
    Performs the auto-tagging for certain Articles and other things
    that require and Article instance first.
    """

    requires_save = instance.do_auto_tag()
    requires_save |= instance.do_tags_to_keywords()
    requires_save |= instance.do_default_site()

    if requires_save:
        # bypass the other processing
        super(Article, instance).save()

def apply_new_tag(sender, instance, created, **kwargs):
    """
    Applies new tags to existing articles that are marked for auto-tagging
    """

    for article in Article.objects.filter(auto_tag=True):
        if article.do_auto_tag():
            # bypass the other processing
            super(Article, article).save()

signals.post_save.connect(article_post_processing, sender=Article)
signals.post_save.connect(apply_new_tag, sender=Tag)
