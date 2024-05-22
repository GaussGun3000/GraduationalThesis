from flask import Flask
from .views import register_blueprints
from pymongo import MongoClient


def create_app():

    app = Flask(__name__)
    app.config.from_object('config.Config')
    # Инициализация клиента MongoDB
    client = MongoClient(app.config['MONGO_URI'])
    app.mongo_client = client
    app.db = client.get_database("GraduationalThesis")

    register_blueprints(app)

    return app
