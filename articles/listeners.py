from django.db.models import signals
from models import Article, Tag

def apply_new_tag(sender, instance, created, **kwargs):
    """
    Applies new tags to existing articles that are marked for auto-tagging
    """

    for article in Article.objects.filter(auto_tag=True):
        article.do_auto_tag()

signals.post_save.connect(apply_new_tag, sender=Tag)
