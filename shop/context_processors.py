from .models import Category, Cart

def extras(request):
    # Récupère toutes les catégories pour les menus de navigation
    categories = Category.objects.all()
    
    cart_count = 0
    
    if request.user.is_authenticated:
        # On utilise filter().first() ou get_or_create pour éviter l'exception DoesNotExist
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Option A : Compter le nombre de PRODUITS différents (ex: 1 iPhone + 1 Mac = 2)
        cart_count = cart.items.count()
    return {
        'categories': categories,
        'cart_count': cart_count
    }