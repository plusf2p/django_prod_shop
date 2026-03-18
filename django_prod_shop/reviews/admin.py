from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'comment_short', 'rating']
    list_display_links = ['product']

    def comment_short(self, obj):
        if len(obj.comment) > 50:
            return obj.comment[:50] + '...'
        return obj.comment[:50]

    comment_short.short_description = 'Описание'
