import uuid
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView
from .models import Product, Category, Cart, CartItem, Order, OrderItem, Size, Capacity, Color
from django.db import transaction
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings
from .forms import ReviewForm
from django.contrib import messages
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse
from weasyprint import HTML
from django.contrib.admin.views.decorators import staff_member_required

# --- Accueil ---
def home(request):
    # .select_related ou .prefetch_related pour optimiser les perfs
    products = Product.objects.all().order_by('-date_ajout')[:8]
    categories = Category.objects.all()
    return render(request, 'core/Home.html', {
        'products': products,
        'categories': categories
    })

# --- Liste des Produits avec Filtres ---
class ProductListView(ListView):
    model = Product
    template_name = 'core/Product_Listing.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('search')
        category_slug = self.request.GET.get('category')
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        sort_by = self.request.GET.get('sort')

        if category_slug:
            queryset = queryset.filter(categorie__slug=category_slug)
        if query:
            queryset = queryset.filter(
                Q(nom__icontains=query) | Q(marque__icontains=query) | Q(description_courte__icontains=query)
            )
        if min_price:
            queryset = queryset.filter(prix__gte=min_price)
        if max_price:
            queryset = queryset.filter(prix__lte=max_price)

        # Tri
        sort_options = {
            'price_asc': 'prix',
            'price_desc': '-prix',
            'oldest': 'date_ajout'
        }
        queryset = queryset.order_by(sort_options.get(sort_by, '-date_ajout'))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context

# --- Détails Produit & Avis ---
class ProductDetailView(DetailView):
    model = Product
    template_name = 'core/Single_Product.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['images'] = self.object.images.all()
        context['reviews'] = self.object.reviews.select_related('user').order_by('-created_at')
        context['similar_products'] = Product.objects.filter(categorie=self.object.categorie).exclude(id=self.object.id)[:4]
        context['review_form'] = ReviewForm()
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Connectez-vous pour laisser un avis.")
            return redirect('login')
        
        self.object = self.get_object()
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = self.object
            review.user = request.user
            review.save()
            messages.success(request, "Avis publié !")
            return redirect('product_detail', slug=self.object.slug)
        return self.render_to_response(self.get_context_data(review_form=form))

# --- Gestion du Panier ---
@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    # Sécurité Stock
    if product.quantite_stocks < 1:
        messages.error(request, "Désolé, ce produit est en rupture de stock.")
        return redirect('product_detail', slug=product.slug)

    cart, _ = Cart.objects.get_or_create(user=request.user)
    
    # Récupération des variantes
    color_id = request.POST.get('color') or None
    size_id = request.POST.get('size') or None
    capacity_id = request.POST.get('capacity') or None
    quantity = int(request.POST.get('quantity', 1))

    # On cherche si l'article avec EXACTEMENT ces variantes existe déjà
    item, created = CartItem.objects.get_or_create(
        cart=cart, 
        product=product,
        color_id=color_id,
        size_id=size_id,
        capacity_id=capacity_id,
        defaults={'quantity': quantity}
    )
    
    if not created:
        item.quantity += quantity
        item.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'cart_count': cart.items.count()})
    
    return redirect('cart_detail')

@login_required
def cart_detail(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('product', 'color', 'size', 'capacity').all()
    return render(request, 'core/Shopping_Cart.html', {'cart': cart, 'cart_items': items})

@login_required
def update_cart_item(request, item_id):
    """Met à jour la quantité d'un article dans le panier"""
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    # On accepte GET (comme dans votre code) ou POST (plus sécurisé pour modifier des données)
    action = request.GET.get('action') or request.POST.get('action')
    
    if action == 'increase':
        if item.quantity < item.product.quantite_stocks:
            item.quantity += 1
            item.save()
        else:
            messages.warning(request, "Stock insuffisant.")
    elif action == 'decrease':
        if item.quantity > 1:
            item.quantity -= 1
            item.save()
        else:
            item.delete()
            return redirect('cart_detail') # On redirige si l'article est supprimé

    # Gestion AJAX pour une expérience fluide
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'quantity': item.quantity,
            'item_total': item.total_price(), # Assurez-vous d'avoir cette méthode dans votre modèle
            'cart_total': item.cart.get_total_price() # Et celle-ci aussi
        })

    return redirect('cart_detail')

@login_required
def cart_remove(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    messages.success(request, "Article retiré du panier.")
    return redirect('cart_detail')

# --- Commande & Paiement ---
from django.db import transaction
from django.contrib import messages

@login_required
@transaction.atomic
def checkout_view(request):
    # Utilisation de select_related pour optimiser les requêtes SQL
    cart = get_object_or_404(Cart.objects.select_related('user'), user=request.user)
    
    if not cart.items.exists():
        messages.warning(request, "Votre panier est vide.")
        return redirect('product_list')

    if request.method == 'POST':
        try:
            # 1. Récupération sécurisée des données du formulaire
            full_name = request.POST.get('full_name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            address = request.POST.get('address')
            
            if not all([full_name, email, phone, address]):
                raise ValueError("Veuillez remplir tous les champs obligatoires.")

            # 2. Création de la commande
            order = Order.objects.create(
                user=request.user,
                full_name=full_name,
                email=email,
                phone=phone,
                address=address,
                city=request.POST.get('city', 'Libreville'),
                order_key=uuid.uuid4().hex,
                total_amount=cart.total_final, # On fige le montant calculé du panier
                shipping_cost=cart.shipping_cost
            )

            # 3. Transfert des articles du panier vers la commande
            for item in cart.items.all():
                # Vérification du stock
                if item.product.quantite_stocks < item.quantity:
                    # Ici, la transaction.atomic annulera la création de 'order' si on lève l'erreur
                    raise ValueError(f"Désolé, le stock pour '{item.product.nom}' est épuisé.")
                
                # Détermination du prix au moment de l'achat
                current_unit_price = item.product.prix_promotionnel if item.product.est_en_promo else item.product.prix

                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    price=current_unit_price,
                    quantity=item.quantity,
                    color=str(item.color.name) if item.color else None,
                    size=str(item.size.name) if item.size else None,
                    capacity=str(item.capacity.name) if item.capacity else None
                )
                
                # Mise à jour du stock
                item.product.quantite_stocks -= item.quantity
                item.product.save()

            # 4. Nettoyage final
            cart.items.all().delete()
            
            # Message de succès et redirection
            messages.success(request, "Votre commande a été validée avec succès !")
            return render(request, 'core/Thank_You.html', {'order': order})

        except ValueError as e:
            messages.error(request, str(e))
            return redirect('checkout_view')
        except Exception as e:
            # Log l'erreur réelle en console pour le debug
            print(f"Erreur Checkout: {e}") 
            messages.error(request, "Une erreur technique est survenue. Veuillez réessayer.")
            return redirect('checkout_view')

    return render(request, 'core/Checkout.html', {'cart': cart})

# --- Historique des Commandes ---

class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'order/order_list.html' # Vérifiez que ce chemin existe
    context_object_name = 'orders'

    def get_queryset(self):
        # On filtre pour que l'utilisateur ne voie que SES commandes
        return Order.objects.filter(user=self.request.user).order_by('-created_at')
    
def delete_order(request, order_id):
    # On récupère la commande appartenant à l'utilisateur
    order = get_object_or_404(Order, id=order_id, user=request.user)
        
    # Optionnel : Sécurité pour empêcher de supprimer une commande déjà payée
    if order.is_paid:
        messages.error(request, "Impossible de supprimer une commande déjà payée.")
    else:
        order.delete()
        messages.success(request, "La commande a été supprimée avec succès.")
            
    return redirect('order_history') # Redirige vers la liste des commandes
    
# --- PDF & Historique ---
@login_required
def order_pdf_download(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    html_string = render_to_string('admin/shop/order/invoice.html', {'order': order})
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    
    response = HttpResponse(html.write_pdf(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Facture_{order.reference}.pdf"'
    return response

@staff_member_required
def order_invoice_admin(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'admin/shop/order/invoice.html', {'order': order})