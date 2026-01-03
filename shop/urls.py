from django.urls import path
from . import views

urlpatterns = [
    # Pages principales
    path('', views.home, name='home'),
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),

    # Panier
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.cart_remove, name='cart_remove'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='cart_update_quantity'),

    # Commande et Checkout
    path('checkout/', views.checkout_view, name='checkout_view'),
    path('mes-commandes/', views.OrderListView.as_view(), name='order_history'),
    path('commande/supprimer/<int:order_id>/', views.delete_order, name='delete_order'),
    path('commande/<int:order_id>/pdf/', views.order_pdf_download, name='order_pdf_download'),

    path('dashboard/order/<int:order_id>/invoice/', views.order_invoice_admin, name='order_invoice_admin'),
]


