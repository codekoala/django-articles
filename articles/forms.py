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

        tags = [Tag.objects.get_or_create(name=t.strip())[0] for t in self.cleaned_data['tags'].split()]
        self.cleaned_data['tags'] = tags
        return self.cleaned_data['tags']

    class Meta:
        model = Article

