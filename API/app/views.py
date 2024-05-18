from flask import Blueprint, jsonify, current_app
from bson.objectid import ObjectId
from .models import User
from dataclasses import asdict

main_blueprint = Blueprint('main', __name__)

@main_blueprint.route('/user/<int:user_tid>', methods=['GET'])
def get_user_by_tid(user_tid):
    user_tid = str(user_tid)
    user_data = current_app.db.Users.find_one({"user_tid": user_tid})
    if user_data:
        user_data['user_oid'] = str(user_data['_id'])  # Преобразуем ObjectId в строку
        del user_data['_id']  # Удаляем оригинальное поле _id, чтобы не было конфликта с user_oid
        user = User(**user_data)
        return jsonify(asdict(user))
    else:
        return jsonify({"error": "User not found"}), 404

