# Backend de l'Application de Dictée

API REST pour l'application de dictée intelligente, développée avec Django et Django REST Framework.

## Fonctionnalités

- Génération de dictées personnalisées
- Gestion des profils utilisateurs
- Analyse des performances
- API RESTful complète
- Authentification JWT

## Technologies utilisées

- Python 3.11+
- Django 5.0
- Django REST Framework
- PostgreSQL
- Celery (pour les tâches asynchrones)
- Redis (pour le cache et les files d'attente)

## Installation

1. Clonez le repository :
```bash
git clone https://github.com/Ebenezer-Bakouan/dicte_backend.git
cd dicte_backend
```

2. Créez un environnement virtuel :
```bash
python -m venv venv
source venv/bin/activate  # Sur Unix/macOS
# ou
.\venv\Scripts\activate  # Sur Windows
```

3. Installez les dépendances :
```bash
pip install -r requirements.txt
```

4. Configurez les variables d'environnement :
```bash
cp .env.example .env
# Éditez .env avec vos paramètres
```

5. Appliquez les migrations :
```bash
python manage.py migrate
```

6. Créez un superutilisateur :
```bash
python manage.py createsuperuser
```

7. Lancez le serveur de développement :
```bash
python manage.py runserver
```

## Structure du projet

```
backend/
├── dictation/           # Application principale
│   ├── api/            # Endpoints API
│   ├── models/         # Modèles de données
│   ├── services/       # Logique métier
│   └── tests/          # Tests unitaires
├── users/              # Gestion des utilisateurs
├── core/               # Configuration Django
└── requirements/       # Dépendances par environnement
```

## API Endpoints

- `/api/auth/` - Authentification
- `/api/dictations/` - Gestion des dictées
- `/api/users/` - Gestion des utilisateurs
- `/api/analytics/` - Statistiques et analyses

## Tests

```bash
python manage.py test
```

## Déploiement

1. Configurez les variables d'environnement de production
2. Collectez les fichiers statiques :
```bash
python manage.py collectstatic
```
3. Lancez le serveur avec Gunicorn :
```bash
gunicorn core.wsgi:application
```

## Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou à soumettre une pull request.

## Licence

MIT 