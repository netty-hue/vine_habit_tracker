from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

from app.config import Config

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)  
    login_manager.login_view = "main.login"

    from app.routes import main
    app.register_blueprint(main)

    # Supprime db.create_all() — Flask-Migrate gère ça maintenant
    
    return app