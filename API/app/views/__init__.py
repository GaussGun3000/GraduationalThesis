from flask import Flask
from .user_views import user_blueprint
from .group_views import group_blueprint
from .task_views import task_blueprint
from .financial_views import financial_blueprint


def register_blueprints(app: Flask):
    app.register_blueprint(user_blueprint)
    app.register_blueprint(group_blueprint)
    app.register_blueprint(task_blueprint)
    app.register_blueprint(financial_blueprint)
