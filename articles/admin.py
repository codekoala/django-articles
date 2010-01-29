from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _
from forms import ArticleAdminForm
from models import Tag, Article

class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'publish_date', 'expiration_date', 'is_active')
    list_filter = ('author', 'is_active', 'publish_date', 'expiration_date', 'sites')
    list_per_page = 25
    search_fields = ('title', 'keywords', 'description', 'content')
    date_hierarchy = 'publish_date'
    form = ArticleAdminForm

    fieldsets = (
        (None, {'fields': ('title', 'content', 'tags', 'markup')}),
        ('Metadata', {
            'fields': ('keywords', 'description',),
            'classes': ('collapse',)
        }),
        ('Relationships', {
            'fields': ('followup_for', 'related_articles'),
            'classes': ('collapse',)
        }),
        ('Scheduling', {'fields': ('publish_date', 'expiration_date')}),
        ('AddThis Button Options', {
            'fields': ('use_addthis_button', 'addthis_use_author', 'addthis_username'),
            'classes': ('collapse',)
        }),
        ('Advanced', {
            'fields': ('slug', 'is_active', 'login_required', 'sites'),
            'classes': ('collapse',)
        }),
    )

    filter_horizontal = ('tags', 'followup_for', 'related_articles')
    prepopulated_fields = {'slug': ('title',)}

    def mark_active(self, request, queryset):
        queryset.update(is_active=True)
    mark_active.short_description = _('Mark select articles as active')

    def mark_inactive(self, request, queryset):
        queryset.update(is_active=False)
    mark_inactive.short_description = _('Mark select articles as inactive')

    actions = (mark_active, mark_inactive)

    def save_model(self, request, obj, form, change):
        """Set the article's author based on the logged in user and make sure at least one site is selected"""

        try:
            author = obj.author
        except User.DoesNotExist:
            obj.author = request.user

        obj.save()

    def queryset(self, request):
        """Limit the list of articles to article posted by this user unless they're a superuser"""

        if request.user.is_superuser:
            return self.model._default_manager.all()
        else:
            return self.model._default_manager.filter(author=request.user)

admin.site.register(Tag)
admin.site.register(Article, ArticleAdmin)
