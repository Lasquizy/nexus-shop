from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import (
    Category, SubCategory, DeliveryZone, Color, 
    Size, Capacity, Product, ProductImage, Review, Cart, CartItem, Order, OrderItem
)
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
import json
from django.utils import timezone
from django.db.models import F

# --- INLINES ---

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ['preview']

    def preview(self, obj):
        if obj.image:
            try:
                return format_html('<img src="{}" style="width: 50px; height: auto; border-radius: 5px;" />', obj.image.url)
            except:
                return "Erreur URL"
        return "Pas d'image"

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ['product', 'color', 'size', 'capacity', 'quantity', 'get_unit_price', 'total_item_price_display']
    readonly_fields = ['get_unit_price', 'total_item_price_display']

    def get_unit_price(self, obj):
        if obj.product:
            price = obj.product.prix_promotionnel if obj.product.est_en_promo else obj.product.prix
            return f"{price} FCFA"
        return "-"
    get_unit_price.short_description = "P.U."

    def total_item_price_display(self, obj):
        return f"{obj.total_item_price} FCFA"
    total_item_price_display.short_description = "Sous-total"

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ('product', 'price', 'quantity', 'color', 'size', 'capacity', 'total_price_display')
    fields = ('product', 'price', 'quantity', 'color', 'size', 'capacity', 'total_price_display')
    extra = 0
    can_delete = False

    def total_price_display(self, obj):
        return f"{obj.total_price} FCFA"
    total_price_display.short_description = "Sous-total"

# --- CONFIGURATIONS ADMIN ---

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('nom', 'categorie', 'prix', 'prix_promotionnel', 'quantite_stocks', 'est_en_promo_icon', 'date_ajout')
    list_filter = ('categorie', 'etat', 'date_ajout', 'livraison_gratuite')
    search_fields = ('nom', 'marque', 'description_courte')
    prepopulated_fields = {'slug': ('nom',)}
    inlines = [ProductImageInline]
    
    fieldsets = (
        ('Informations Générales', {'fields': ('nom', 'slug', 'categorie', 'subcategorie', 'etat', 'marque')}),
        ('Contenu & Médias', {'fields': ('description_courte', 'description_longue', 'caracteristiques', 'video_demo')}),
        ('Prix & Promotion', {'fields': (('prix', 'prix_promotionnel'), ('date_debut_promo', 'date_fin_promo'))}),
        ('Stock & Livraison', {'fields': (('quantite_stocks', 'seuil_stocks_bas'), 'zones_livraison', ('frais_livraison_fixe', 'livraison_gratuite'), ('delai_min', 'delai_max'))}),
        ('Variantes', {'fields': ('colors', 'sizes', 'capacities'), 'classes': ('collapse',)}),
        ('Politique', {'fields': ('politique_retour', 'instructions_retour', 'garantie_produit')}),
    )

    def est_en_promo_icon(self, obj):
        return obj.est_en_promo
    est_en_promo_icon.boolean = True
    est_en_promo_icon.short_description = "En Promo ?"

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'items_count', 'total_price_display', 'updated_at')
    inlines = [CartItemInline]

    def items_count(self, obj):
        return obj.items.count()
    items_count.short_description = "Articles"

    def total_price_display(self, obj):
        return f"{obj.total_price} FCFA"
    total_price_display.short_description = "Total"

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('reference', 'full_name', 'status_colored', 'total_amount_display', 'is_paid', 'print_invoice')
    list_filter = ('status', 'is_paid', 'created_at', 'city')
    search_fields = ('reference', 'full_name', 'email', 'phone')
    readonly_fields = ('reference', 'user', 'total_amount', 'shipping_cost', 'created_at', 'updated_at', 'order_key')
    inlines = [OrderItemInline]
    actions = ['make_paid']

    fieldsets = (
        ('Informations Générales', {'fields': ('reference', 'user', 'status', 'is_paid')}),
        ('Détails Client & Livraison', {'fields': ('full_name', 'email', 'phone', 'address', 'city')}),
        ('Calcul Financier', {'fields': ('total_amount', 'shipping_cost', 'order_key')}),
        ('Dates', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def total_amount_display(self, obj):
        return f"{obj.total_amount} FCFA"
    total_amount_display.short_description = "Montant Total"

    def status_colored(self, obj):
        colors = {'PENDING': '#FFA500', 'PAID': '#28A745', 'SHIPPED': '#17A2B8', 'DELIVERED': '#218838', 'CANCELLED': '#DC3545'}
        return mark_safe(f'<b style="color:{colors.get(obj.status, "black")};">{obj.get_status_display()}</b>')
    status_colored.short_description = "Statut"

    @admin.action(description="Marquer comme Payées")
    def make_paid(self, request, queryset):
        queryset.update(is_paid=True, status='PAID')

    def print_invoice(self, obj):
        if obj.id:
            # On essaie de récupérer l'URL (avec ou sans namespace 'shop')
            try:
                url = reverse('order_invoice_admin', args=[obj.id])
            except:
                url = reverse('shop:order_invoice_admin', args=[obj.id])
                
            return format_html(
                '<a href="{}" target="_blank" '
                'style="background-color: #447e9b; color: white; padding: 5px 10px; '
                'border-radius: 4px; text-decoration: none; font-weight: bold;">'
                '🖨️ Facture</a>', 
                url
            )
        return ""
    print_invoice.short_description = "Action"

# --- AUTRES ENREGISTREMENTS ---
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'show_img')
    prepopulated_fields = {'slug': ('name',)}
    def show_img(self, obj):
        if obj.img:
            return format_html('<img src="{}" style="width: 30px; height: auto;" />', obj.img.url)
        return "-"

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    readonly_fields = ('created_at',)

admin.site.register(SubCategory)
admin.site.register(DeliveryZone)
admin.site.register(Color)
admin.site.register(Size)
admin.site.register(Capacity)

# ==========================================
# 1. SAUVEGARDE DE LA VUE INDEX ORIGINALE
# ==========================================
# On stocke la fonction de base pour éviter la boucle infinie (RecursionError)
original_admin_index = admin.site.index

# ==========================================
# 2. DÉFINITION DE LA VUE PERSONNALISÉE
# ==========================================
def custom_admin_index(request, extra_context=None):
    extra_context = extra_context or {}
    now = timezone.now()

    # --- A. CALCULS POUR LES WIDGETS (MOIS EN COURS) ---
    orders_month = Order.objects.filter(
        is_paid=True, 
        created_at__year=now.year, 
        created_at__month=now.month
    )

    # Chiffre d'Affaires (CA)
    ca_mois = orders_month.aggregate(total=Sum('total_amount'))['total'] or 0

    # Bénéfice (Prix vente - Prix achat) * Quantité
    # On utilise F() pour faire le calcul directement en SQL
    benefice_mois = OrderItem.objects.filter(order__in=orders_month).aggregate(
        total_benefice=Sum((F('price') - F('product__prix_achat')) * F('quantity'))
    )['total_benefice'] or 0

    # Nombre de commandes payées ce mois
    nb_commandes = orders_month.count()

    # --- B. DONNÉES POUR LES GRAPHIQUES (CHART.JS) ---
    # Évolution des ventes sur les 7 derniers jours
    sales_data = Order.objects.filter(is_paid=True).annotate(date=TruncDate('created_at')) \
        .values('date').annotate(total=Sum('total_amount')).order_by('date')[:7]

    # Top 5 des produits les plus vendus
    top_products = OrderItem.objects.values('product__nom') \
        .annotate(total_qty=Sum('quantity')).order_by('-total_qty')[:5]

    # --- C. INJECTION DANS LE CONTEXTE ---
    # Données Widgets
    extra_context['ca_mois'] = ca_mois
    extra_context['benefice_mois'] = benefice_mois
    extra_context['nb_commandes'] = nb_commandes

    # Données Graphiques (formatées en JSON pour JavaScript)
    extra_context['sales_labels'] = json.dumps([str(x['date']) for x in sales_data])
    extra_context['sales_values'] = json.dumps([float(x['total']) for x in sales_data])
    extra_context['top_prod_labels'] = json.dumps([x['product__nom'] for x in top_products])
    extra_context['top_prod_values'] = json.dumps([int(x['total_qty']) for x in top_products])
    
    stock_alert_products = Product.objects.filter(
        quantite_stocks__lte=F('seuil_stocks_bas')
    ).select_related('categorie')
    
    nb_stock_alerts = stock_alert_products.count()

    # Injection dans le contexte
    extra_context['nb_stock_alerts'] = nb_stock_alerts
    extra_context['stock_alert_products'] = stock_alert_products
    
    return original_admin_index(request, extra_context)

# ==========================================
# 3. REMPLACEMENT DE LA VUE PAR DÉFAUT
# ==========================================
admin.site.index = custom_admin_index