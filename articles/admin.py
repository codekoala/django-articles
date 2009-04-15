from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from models import Category, Article

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'image')
    prepopulated_fields = {'slug': ('name',)}

class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'publish_date', 'expiration_date', 'is_active', 'is_commentable')
    list_filter = ('author', 'is_active', 'publish_date', 'expiration_date')
    list_per_page = 25
    search_fields = ('title', 'keywords', 'description', 'content')
    date_hierarchy = 'publish_date'

    fieldsets = (
        (None, {'fields': ('title', 'content', 'markup', 'categories')}),
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
            'fields': ('slug', 'is_active', 'is_commentable', 'display_comments', 'login_required'),
            'classes': ('collapse',)
        }),
    )

    filter_horizontal = ('categories', 'followup_for', 'related_articles')
    prepopulated_fields = {'slug': ('title',)}

    def mark_active(self, request, queryset):
        queryset.update(is_active=True)
    mark_active.short_description = _('Mark select articles as active')

    def mark_inactive(self, request, queryset):
        queryset.update(is_active=False)
    mark_inactive.short_description = _('Mark select articles as inactive')

    def mark_commentable(self, request, queryset):
        queryset.update(is_commentable=True)
    mark_commentable.short_description = _('Mark select articles as commentable')

    def mark_noncommentable(self, request, queryset):
        queryset.update(is_commentable=False)
    mark_noncommentable.short_description = _('Mark select articles as noncommentable')

    actions = (mark_active, mark_inactive, mark_commentable, mark_noncommentable)

    def save_model(self, request, obj, form, change):
        try:
            author = obj.author
        except User.DoesNotExist:
            obj.author = request.user
        obj.save()

    def queryset(self, request):
        if request.user.is_superuser:
            return self.model._default_manager.all()
        else:
            return self.model._default_manager.filter(author=request.user)

admin.site.register(Category, CategoryAdmin)
admin.site.register(Article, ArticleAdmin)