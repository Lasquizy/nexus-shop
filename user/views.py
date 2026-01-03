from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from .forms import RegisterForm
from django.contrib.auth.forms import AuthenticationForm

def register_view(request):
    # Sécurité : Si l'utilisateur est déjà connecté, on le redirige vers l'accueil
    if request.user.is_authenticated:
        return redirect("product_list")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # On spécifie le backend si nécessaire (optionnel mais recommandé)
            login(request, user) 
            messages.success(request, f"Bienvenue {user.username}, votre compte a été créé avec succès !")
            return redirect("product_list")
        else:
            # En cas d'erreur de formulaire (mot de passe trop court, etc.)
            messages.error(request, "Erreur lors de l'inscription. Veuillez vérifier les informations saisies.")
    else:
        form = RegisterForm()
        
    return render(request, "user/register.html", {"form": form})

def logout_view(request):
    # Il est recommandé de vérifier si la méthode est POST pour la déconnexion (sécurité)
    # Mais pour une implémentation simple via un lien <a>, on garde ceci :
    logout(request)
    messages.info(request, "Vous avez été déconnecté.")
    return redirect("product_list")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("product_list")
        
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"Bon retour, {username} !")
                next_url = request.GET.get('next', 'product_list')
                return redirect(next_url)
        else:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
    else:
        form = AuthenticationForm()
    return render(request, "user/login.html", {"form": form})