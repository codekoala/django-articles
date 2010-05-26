from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _
from forms import ArticleAdminForm
from models import Tag, Article, ArticleStatus, Attachment

class ArticleStatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_live')
    list_filter = ('is_live',)
    search_fields = ('name',)

class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 5
    max_num = 15

class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'author', 'publish_date', 'expiration_date', 'is_active')
    list_filter = ('author', 'status', 'is_active', 'publish_date', 'expiration_date', 'sites')
    list_per_page = 25
    search_fields = ('title', 'keywords', 'description', 'content')
    date_hierarchy = 'publish_date'
    form = ArticleAdminForm
    inlines = [
        AttachmentInline,
    ]

    fieldsets = (
        (None, {'fields': ('title', 'content', 'tags', 'markup', 'status')}),
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

    def get_actions(self, request):
        actions = super(ArticleAdmin, self).get_actions(request)

        def dynamic(name, status):
            def status_func(self, request, queryset):
                queryset.update(status=status)

            status_func.__name__ = name
            status_func.short_description = _('Set status of selected to "%s"' % status)
            return status_func

        for status in ArticleStatus.objects.all():
            name = 'mark_status_%i' % status.id
            actions[name] = (dynamic(name, status), name, _('Set status of selected to "%s"' % status))

        return actions

    actions = [mark_active, mark_inactive]

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
admin.site.register(ArticleStatus, ArticleStatusAdmin)

