from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class RegisterForm(UserCreationForm):
    # On force l'email à être obligatoire
    email = forms.EmailField(
        required=True, 
        label="Adresse e-mail",
        help_text="Requis pour recevoir vos confirmations de commande."
    )

    class Meta:
        model = User
        # On définit l'ordre d'affichage des champs
        fields = ["username", "email"]
        labels = {
            "username": "Nom d'utilisateur",
        }