from django.contrib import admin

from .models import Product, Category


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'category', 'quantity',  'reserved_quantity',
        'description_short', 'slug', 'price', 'created_at',
    ]
    list_display_links = ['title']
    prepopulated_fields = {"slug": ["title"]}

    def description_short(self, obj: Product) -> str:
        if len(obj.description) > 50:
            return obj.description[:50] + '...'
        return obj.description[:50]

    description_short.short_description = 'Описание'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['title', 'description_short', 'slug', 'created_at']
    list_display_links = ['title']
    prepopulated_fields = {"slug": ["title"]}

    def description_short(self, obj: Category) -> str:
        if len(obj.description) > 50:
            return obj.description[:50] + '...'
        return obj.description[:50]

    description_short.short_description = 'Описание'
