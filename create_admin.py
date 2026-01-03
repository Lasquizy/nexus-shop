import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings') # Remplacez 'config' par le nom de votre dossier projet
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'votre-email@gmail.com', 'votre-mot-de-passe-robuste')
    print("Superuser créé avec succès !")
else:
    print("Le superuser existe déjà.")