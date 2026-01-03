from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User # Importe ton modèle Cart

from shop.models import Cart 

# --- Intégrer le panier directement dans la fiche utilisateur ---
class CartInline(admin.StackedInline):
    model = Cart
    can_delete = False
    verbose_name_plural = 'Panier actif'
    readonly_fields = ['created_at', 'updated_at']

# --- Personnalisation de l'UserAdmin ---
class MyUserAdmin(UserAdmin):
    # Ajouter le panier en bas de la fiche utilisateur
    inlines = (CartInline,)
    
    # Colonnes affichées dans la liste des utilisateurs
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_cart_items')
    
    # Ajouter des filtres pour identifier rapidement les clients vs staff
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')

    def get_cart_items(self, obj):
        """Affiche le nombre d'articles dans le panier de l'utilisateur"""
        try:
            return obj.cart.items_count
        except:
            return 0
    get_cart_items.short_description = 'Articles en panier'

# On retire l'UserAdmin par défaut de Django et on enregistre le nôtre
admin.site.unregister(User)
admin.site.register(User, MyUserAdmin)

# --- Optionnel : Configuration du site Admin ---
admin.site.site_header = "Administration Gabon E-shop"
admin.site.site_title = "E-shop Admin"
admin.site.index_title = "Gestion de la plateforme"