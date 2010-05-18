from django import forms
from django.utils.translation import ugettext_lazy as _
from models import Article, Tag

class ArticleAdminForm(forms.ModelForm):
    tags = forms.CharField(initial='', required=False,
                           widget=forms.TextInput(attrs={'size': 100}),
                           help_text=_('Words that describe this article'))

    def __init__(self, *args, **kwargs):
        """Sets the list of tags to be a string"""

        instance = kwargs.get('instance', None)
        if instance:
            init = kwargs.get('initial', {})
            init['tags'] = ' '.join([t.name for t in instance.tags.all()])
            kwargs['initial'] = init

        super(ArticleAdminForm, self).__init__(*args, **kwargs)

    def clean_tags(self):
        """Turns the string of tags into a list"""

        tag = lambda n: Tag.objects.get_or_create(name=Tag.clean_tag(n))[0]
        tags = [tag(t) for t in self.cleaned_data['tags'].split()]
        self.cleaned_data['tags'] = tags
        return self.cleaned_data['tags']

    class Meta:
        model = Article

    class Media:
        css = {
            'all': ('css/jquery.autocomplete.css',),
        }
        js = (
            'js/jquery-1.4.1.min.js',
            'js/jquery.bgiframe.min.js',
            'js/jquery.autocomplete.pack.js',
            'js/tag_autocomplete.js',
        )

