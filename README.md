# Structure de base Flask — Projet de fin d'année L3

Structure minimale mais complète pour démarrer un projet Flask : authentification simple + un exemple de CRUD (tâches), à adapter selon le sujet de chaque projet.

## Arborescence

```
flask_projet_base/
├── app/
│   ├── __init__.py       -> Application Factory (create_app), init des extensions
│   ├── config.py         -> Configuration (clé secrète, base SQLite)
│   ├── models.py         -> Modèles SQLAlchemy (User, Tache)
│   ├── forms.py          -> Formulaires WTForms (inscription, connexion, tâche)
│   ├── routes.py         -> Toutes les routes (blueprint "main")
│   ├── templates/        -> Fichiers HTML (Jinja2 + Bootstrap 5)
│   └── static/
│       └── style.css
├── run.py                -> Fichier à lancer pour démarrer le serveur
├── requirements.txt      -> Bibliothèques nécessaires
└── app.db                -> Base SQLite (créée automatiquement au 1er lancement)
```

## Installation

```bash
python -m venv venv
source venv/bin/activate      # Sous Windows : venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Ouvrir ensuite : http://127.0.0.1:5000

## Ce que contient le squelette

- **Inscription / Connexion / Déconnexion** avec mots de passe hashés (Flask-Login + Werkzeug)
- **Un exemple de CRUD** (modèle `Tache` lié à un `User`) : créer, terminer, supprimer
- **Relation 1-N** entre `User` et `Tache` (exemple à reproduire pour vos propres modèles)
- **Base de données SQLite** créée automatiquement au premier lancement (fichier `app.db`)

## Comment étendre ce squelette pour votre propre projet

1. **Ajouter un modèle** : ouvrez `models.py`, créez une nouvelle classe héritant de `db.Model` (copiez le modèle `Tache` comme exemple).
2. **Ajouter un formulaire** : ouvrez `forms.py`, créez une classe héritant de `FlaskForm`.
3. **Ajouter des routes** : ouvrez `routes.py`, ajoutez vos fonctions avec `@main.route(...)`.
4. **Ajouter un template** : créez un fichier `.html` dans `templates/`, en commençant par `{% extends "base.html" %}`.

Pas besoin de toucher à `__init__.py` ni `config.py` sauf si vous changez le nom de la base de données ou ajoutez une nouvelle extension.

## Remarque importante

La clé `SECRET_KEY` dans `config.py` est volontairement simple pour le développement. Pensez à la changer si vous déployez le projet.
