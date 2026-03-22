from django.contrib import admin

from .models import OrderItem, Order


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ['product', 'price', 'quantity']
    readonly_fields = ['price']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    model = Order
    list_display = ['order_id', 'user', 'total_price', 'status']
    list_display_links = ['order_id']
    inlines = [OrderItemInline]
