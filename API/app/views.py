from flask import Blueprint, request, jsonify
from .models import User, Group  # примерно так

main_blueprint = Blueprint('main', __name__)

@main_blueprint.route('/users', methods=['GET'])
def get_users():
    # Ваш код для получения пользователей
    return jsonify([])

@main_blueprint.route('/users', methods=['POST'])
def create_user():
    # Ваш код для создания нового пользователя
    return jsonify({}), 201
