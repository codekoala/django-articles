from django.contrib import admin
from django.contrib.auth.models import User
from models import Category, Article

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'image')
    prepopulated_fields = {'slug': ('name',)}

class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'publish_date', 'expiration_date', 'is_active')
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
        ('Advanced', {
            'fields': ('slug', 'is_active', 'is_commentable',),
            'classes': ('collapse',)
        }),
    )

    filter_horizontal = ('categories', 'followup_for', 'related_articles')
    prepopulated_fields = {'slug': ('title',)}

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