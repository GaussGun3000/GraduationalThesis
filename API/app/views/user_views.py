from flask import Blueprint, jsonify, current_app, request
from bson.objectid import ObjectId

from ..models import User
from dataclasses import asdict
from ..auth import token_required


user_blueprint = Blueprint('user', __name__)


def validate_user_schema(data: dict) -> User | None:
    try:
        oid = data.pop('user_oid', '-')
        user = User(user_oid=oid, **data)
        return user
    except TypeError as e:
        print(e)
        return None


@user_blueprint.route('/user/<int:user_tid>', methods=['GET'])
@token_required
def get_user_by_tid(user_tid):
    user_data = current_app.db.Users.find_one({"user_tid": user_tid})
    if user_data:
        user_data['user_oid'] = str(user_data['_id'])  # Преобразуем ObjectId в строку
        del user_data['_id']  # Удаляем оригинальное поле _id, чтобы не было конфликта с user_oid
        user = User(**user_data)
        return jsonify(asdict(user))
    else:
        return jsonify({"error": "User not found"}), 404


@user_blueprint.route('/user/oid/<string:user_oid>', methods=['GET'])
@token_required
def get_user_by_oid(user_oid):
    user_data = current_app.db.Users.find_one({"_id": ObjectId(user_oid)})
    if user_data:
        user_data['user_oid'] = str(user_data['_id'])
        del user_data['_id']
        user = User(**user_data)
        return jsonify(asdict(user))
    else:
        return jsonify({"error": "User not found"}), 404


@user_blueprint.route('/user/tid_list', methods=['GET'])
@token_required
def get_all_user_tids():
    users = current_app.db.Users.find({}, {"user_tid": 1})
    user_tids = [user['user_tid'] for user in users]
    return jsonify({"user_tids": user_tids}), 200


@user_blueprint.route('/user', methods=['POST'])
@token_required
def create_user():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 400

    user = validate_user_schema(data)
    if not user:
        return jsonify({"error": "Incorrect data structure for User"}), 400

    existing_user = current_app.db.Users.find_one({"user_tid": user.user_tid})
    if existing_user:
        return jsonify({"error": "User with this Telegram ID (tid) already exists"}), 400

    user_dict = (asdict(user))
    user_dict.pop('user_oid', None)

    user_id = current_app.db.Users.insert_one(user_dict).inserted_id
    return jsonify({"user_oid": str(user_id)}), 201


@user_blueprint.route('/user/<int:user_tid>', methods=['PUT'])
@token_required
def update_user(user_tid):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 400

    user = validate_user_schema(data)
    if not user:
        return jsonify({"error": "Incorrect data structure for User"}), 400

    result = current_app.db.Users.update_one({"user_tid": user_tid}, {"$set": data})
    if result.matched_count > 0:
        return jsonify({"message": "User updated successfully"}), 200
    else:
        return jsonify({"error": "User not found"}), 404


@user_blueprint.route('/user/oid/<string:user_oid>', methods=['PUT'])
@token_required
def update_user_by_oid(user_oid):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 400

    if not validate_user_schema(data):
        return jsonify({"error": "Incorrect data structure for User"}), 400
    result = current_app.db.Users.update_one({"_id": ObjectId(user_oid)}, {"$set": data})
    if result.matched_count > 0:
        return jsonify({"message": "User updated successfully"}), 200
    else:
        return jsonify({"error": "User not found"}), 404


@user_blueprint.route('/user/notifications/<int:user_tid>', methods=['PUT'])
@token_required
def update_user_notifications(user_tid):
    data = request.get_json()
    if not data or 'notification_settings' not in data:
        return jsonify({"error": "Invalid input"}), 400

    notification_status = data['notification_settings']
    user = current_app.db.Users.find_one({"user_tid": user_tid})
    if not user:
        return jsonify({"error": "User not found"}), 404

    notification_settings = user.get('notification_settings', {})
    notification_settings['notifications'] = notification_status
    result = current_app.db.Users.update_one(
        {"user_tid": user_tid},
        {"$set": {"notification_settings": notification_settings}})

    if result.matched_count > 0:
        return jsonify({"message": "User notification settings updated successfully"}), 200
    else:
        return jsonify({"error": "Failed to update user notification settings"}), 500




@user_blueprint.route('/user/<int:user_tid>', methods=['DELETE'])
@token_required
def delete_user(user_tid):
    result = current_app.db.Users.delete_one({"user_tid": user_tid})
    if result.deleted_count > 0:
        return jsonify({"message": "User deleted successfully"}), 200
    else:
        return jsonify({"error": "User not found"}), 404


@user_blueprint.route('/user/oid/<string:user_oid>', methods=['DELETE'])
@token_required
def delete_user_by_oid(user_oid):
    result = current_app.db.Users.delete_one({"_id": ObjectId(user_oid)})
    if result.deleted_count > 0:
        return jsonify({"message": "User deleted successfully"}), 200
    else:
        return jsonify({"error": "User not found"}), 404
