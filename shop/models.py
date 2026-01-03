from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import uuid
import datetime

# --- Modèles Annexes ---

class Category(models.Model):
     name = models.CharField(max_length=100, unique=True)
     desc = models.TextField(blank=True)
     slug = models.SlugField(unique=True, blank=True)
     img = models.ImageField(upload_to='categories/', blank=True, null=True)

     class Meta:
        verbose_name = "Catégorie"
    
     def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

     def __str__(self): return self.name

class SubCategory(models.Model):
     category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
     name = models.CharField(max_length=100)
    
     class Meta:
        verbose_name = "Sous-catégorie"
        unique_together = ('category', 'name') # Évite les doublons de noms dans une même catégorie

     def __str__(self): 
         
        return f"{self.category.name} > {self.name}"

class DeliveryZone(models.Model):
     name = models.CharField(max_length=100, unique=True)

     class Meta:
        verbose_name = "Zone de livraison"
        verbose_name_plural = "Zones de livraison"

     def __str__(self): return self.name

class Color(models.Model):
     name = models.CharField(max_length=50)
     code_hex = models.CharField(max_length=7, blank=True, help_text="Ex: #FF0000")
     def __str__(self): return self.name

class Size(models.Model):
     name = models.CharField(max_length=20)
     def __str__(self): return self.name

class Capacity(models.Model):
     name = models.CharField(max_length=50)
     class Meta:
        verbose_name = "Capacité"
     def __str__(self): return self.name

# --- Modèle Principal ---

class Product(models.Model):
    ETAT_CHOICES = [('neuf', 'Neuf'), ('occasion', 'Occasion')]
    RETOUR_CHOICES = [('14J', 'Retour 14J'), ('30J', 'Retour 30J'), ('NONE', 'Pas de retour')]
    GARANTIE_CHOICES = [('2ANS', 'Garantie 2 ans'), ('COM', 'Garantie commerciale'), ('NONE', 'Pas de garantie')]

    # Nom & Catégories
    nom = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True, max_length=255)
    categorie = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    subcategorie = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True, blank=True)
    etat = models.CharField(max_length=20, choices=ETAT_CHOICES, default='neuf')
    marque = models.CharField(max_length=100, blank=True)

    # Description
    description_courte = models.TextField(max_length=500)
    description_longue = models.TextField()
    caracteristiques = models.TextField(blank=True)
    fiche_technique = models.TextField(blank=True)
    
    # Relations Multiple
    colors = models.ManyToManyField(Color, blank=True)
    sizes = models.ManyToManyField(Size, blank=True)
    capacities = models.ManyToManyField(Capacity, blank=True)

    # Médias
    video_demo = models.FileField(upload_to='products/videos/', blank=True, null=True)

    # Prix
    prix = models.DecimalField(max_digits=12, decimal_places=2)
    prix_achat = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Prix d'achat (Coût)")
    prix_promotionnel = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    date_debut_promo = models.DateTimeField(null=True, blank=True)
    date_fin_promo = models.DateTimeField(null=True, blank=True)

    # Stocks
    quantite_stocks = models.PositiveIntegerField(default=0)
    seuil_stocks_bas = models.PositiveIntegerField(default=5)

    # Livraison
    zones_livraison = models.ManyToManyField(DeliveryZone, blank=True)
    frais_livraison_fixe = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    livraison_gratuite = models.BooleanField(default=False)
    delai_min = models.PositiveIntegerField(default=1, help_text="Jours min")
    delai_max = models.PositiveIntegerField(default=3, help_text="Jours max")

    # Politique de retour & Garantie
    politique_retour = models.CharField(max_length=10, choices=RETOUR_CHOICES, default='14J')
    instructions_retour = models.TextField(blank=True)
    garantie_produit = models.CharField(max_length=10, choices=GARANTIE_CHOICES, default='NONE')

    # Dates
    date_ajout = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    @property
    def est_en_promo(self):
        """Vérifie si la promotion est actuellement valide"""
        now = timezone.now()
        if self.prix_promotionnel and self.date_debut_promo and self.date_fin_promo:
            return self.date_debut_promo <= now <= self.date_fin_promo
        return False # Toujours renvoyer False si les conditions ne sont pas réunies

    @property
    def get_price(self):
        """Retourne le prix actuel (promo ou normal)"""
        if self.est_en_promo:
            return self.prix_promotionnel
        return self.prix

    @property
    def benefice_unitaire(self):
        """Calcule la marge brute par unité"""
        return self.get_price - self.prix_achat

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.nom)
            self.slug = base_slug
            counter = 1
            while Product.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    # Correction de l'indentation ici (doit être au niveau de def save)
    def __str__(self):
        return self.nom

# Modèle pour plusieurs images
class ProductImage(models.Model):
     product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
     image = models.ImageField(upload_to='products/images/')

class Review(models.Model):
     product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
     # Utilisation de AUTH_USER_MODEL pour plus de flexibilité
     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
     rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
     comment = models.TextField()
     created_at = models.DateTimeField(auto_now_add=True)

class Cart(models.Model):
     user = models.OneToOneField(
     settings.AUTH_USER_MODEL, 
     on_delete=models.CASCADE, 
     related_name="cart",
     null=True, blank=True
     )
     created_at = models.DateTimeField(auto_now_add=True)
     updated_at = models.DateTimeField(auto_now=True)

     def __str__(self):
        return f"Panier de {self.user.username if self.user else 'Invité'}"

     @property
     def total_price(self):
        """Calcule le prix total de tous les articles du panier"""
     # Utilise total_item_price défini dans CartItem
        return sum(item.total_item_price for item in self.items.all())

     @property
     def items_count(self):
        """Nombre total d'articles (somme des quantités)"""
        return sum(item.quantity for item in self.items.all())
    
     @property
     def shipping_cost(self):
        """Calcule les frais de livraison optimisés"""
        # .select_related('product') évite de refaire une requête SQL par article
        items = self.items.select_related('product').all()
    
        if not items.exists():
            return 0
        
        # 1. Si un seul produit a la livraison gratuite, tout est gratuit
        if any(item.product.livraison_gratuite for item in items):
            return 0
    
        # 2. On récupère les frais fixes en s'assurant qu'ils ne sont pas None
        costs = [
            item.product.frais_livraison_fixe 
                for item in items 
            if item.product.frais_livraison_fixe is not None
            ]
        
        return max(costs) if costs else 0

     @property
     def total_final(self):
        """Somme totale : Articles + Livraison"""
        # On s'assure de retourner un type consistant (Decimal)
        return Decimal(self.total_price) + Decimal(self.shipping_cost)

class CartItem(models.Model):
     cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
     product = models.ForeignKey(Product, on_delete=models.CASCADE)

     # Options choisies par le client
     color = models.ForeignKey(Color, on_delete=models.SET_NULL, null=True, blank=True)
     size = models.ForeignKey(Size, on_delete=models.SET_NULL, null=True, blank=True)
     capacity = models.ForeignKey(Capacity, on_delete=models.SET_NULL, null=True, blank=True)
    
     quantity = models.PositiveIntegerField(default=1)

     def __str__(self):
        return f"{self.quantity} x {self.product.nom}"

     @property
     def total_item_price(self):
        # On récupère le prix (promo ou normal)
        price = self.product.prix_promotionnel if self.product.est_en_promo else self.product.prix
            
        # SÉCURITÉ : Si 'price' est None pour une raison quelconque, on utilise 0.00
        if price is None:
            price = Decimal('0.00')
                
        return self.product.get_price * self.quantity

class Order(models.Model):
     STATUS_CHOICES = [
     ('PENDING', 'En attente'),
     ('PAID', 'Payée / En préparation'),
     ('SHIPPED', 'Expédiée'),
     ('DELIVERED', 'Livrée'),
     ('CANCELLED', 'Annulée'),
     ]

     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    
     # Informations de livraison
     full_name = models.CharField(max_length=255, verbose_name="Nom complet")
     email = models.EmailField()
     phone = models.CharField(max_length=20, verbose_name="Téléphone")
     address = models.TextField(verbose_name="Adresse exacte")
     city = models.CharField(max_length=100, default="Libreville")
    
     # Financier
     total_amount = models.DecimalField(max_digits=12, decimal_places=2)
     shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
     # Suivi
     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
     is_paid = models.BooleanField(default=False)
     order_key = models.CharField(max_length=255, null=True, blank=True)
     reference = models.CharField(max_length=20, unique=True, editable=False, blank=True)
    
     created_at = models.DateTimeField(auto_now_add=True)
     updated_at = models.DateTimeField(auto_now=True)

     class Meta:
        ordering = ['-created_at']
        verbose_name = "Commande"

     def save(self, *args, **kwargs):
        if not self.reference:
            # Boucle pour garantir l'unicité absolue de la référence
            while True:
                unique_id = uuid.uuid4().hex.upper()[:8]
                new_ref = f"NEX-{datetime.datetime.now().year}-{unique_id}"
                if not Order.objects.filter(reference=new_ref).exists():
                    self.reference = new_ref
                    break
        super().save(*args, **kwargs)

     def __str__(self):
        return f"Commande {self.reference} - {self.user.username}"
     
     @property
     def get_cart_total(self):
        return sum(item.total_price for item in self.items.all())

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    
    color = models.CharField(max_length=50, blank=True, null=True)
    size = models.CharField(max_length=50, blank=True, null=True)
    capacity = models.CharField(max_length=50, blank=True, null=True)
    
    price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.product.nom if self.product else 'Produit supprimé'} (x{self.quantity})"

    @property
    def total_price(self):
        # Sécurité : utilise Decimal('0.00') si price est None
        p = self.price if self.price is not None else Decimal('0.00')
        return p * self.quantity