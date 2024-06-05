from flask import Blueprint, jsonify, request, current_app

from ..auth import token_required
from ..models import Group, GroupMember
from dataclasses import asdict
group_blueprint = Blueprint('group', __name__)
from bson.objectid import ObjectId


def validate_group_schema(data: dict) -> Group | None:
    try:
        oid = data.pop('group_oid', '-')
        members = data.pop('members', [])
        validated_members = []
        for member in members:
            if isinstance(member, dict):
                validated_member = GroupMember(**member)
                validated_members.append(validated_member)
            elif isinstance(member, GroupMember):
                validated_members.append(member)
            else:
                raise TypeError("Member must be a dict or GroupMember instance")
        group = Group(group_oid=oid, members=validated_members, **data)
        return group
    except TypeError as e:
        print(e)
        return None


@group_blueprint.route('/group/<string:group_oid>/admins', methods=['GET'])
@token_required
def get_group_admins(group_oid):
    group = current_app.db.Groups.find_one({"_id": ObjectId(group_oid)})
    if not group:
        return jsonify({"error": "Group not found"}), 404

    admins = []
    for member in group['members']:
        if member['role'] == 'admin' or member['role'] == 'creator':
            admins.append(member)

    return jsonify(admins), 200


@group_blueprint.route('/group/user/<string:user_tid>', methods=['GET'])
@token_required
def get_groups_by_user_tid(user_tid):
    # Поиск пользователя по user_tid
    user = current_app.db.Users.find_one({"user_tid": int(user_tid)}, {"_id": 1})
    if not user:
        return jsonify({"error": "User not found"}), 404

    user_oid = str(user['_id'])
    groups = current_app.db.Groups.find(
        {"members": {"$elemMatch": {"member_oid": user_oid, "role": {"$ne": "creator"}}}})
    group_oids = [str(group["_id"]) for group in groups]

    return jsonify(group_oids), 200


@group_blueprint.route('/group/user/<string:user_tid>/created', methods=['GET'])
@token_required
def check_user_created_group(user_tid):
    # Поиск пользователя по user_tid
    user = current_app.db.Users.find_one({"user_tid": int(user_tid)}, {"_id": 1})
    if not user:
        return jsonify({"error": "User not found"}), 404

    user_oid = str(user['_id'])

    created_group = current_app.db.Groups.find_one(
        {"members": {"$elemMatch": {"member_oid": user_oid, "role": "creator"}}})
    if created_group:
        return jsonify({"created_group": str(created_group.get('_id'))}), 200
    else:
        return jsonify({"created_group": False}), 200


@group_blueprint.route('/group/<string:group_oid>', methods=['GET'])
@token_required
def get_group_by_oid(group_oid):
    group_data = current_app.db.Groups.find_one({"_id": ObjectId(group_oid)})
    if group_data:
        group_data['group_oid'] = str(group_data['_id'])
        del group_data['_id']
        group = validate_group_schema(group_data)
        return jsonify(asdict(group))
    else:
        return jsonify({"error": "Group not found"}), 404


@group_blueprint.route('/group', methods=['POST'])
@token_required
def create_group():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 400

    group = validate_group_schema(data)
    if not group:
        return jsonify({"error": "Incorrect data structure for Group"}), 400

    group_dict = asdict(group)
    group_dict.pop('group_oid', None)
    group_id = current_app.db.Groups.insert_one(group_dict).inserted_id
    return jsonify({"group_oid": str(group_id)}), 201


@group_blueprint.route('/group/<string:group_oid>', methods=['PUT'])
@token_required
def update_group(group_oid):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 400

    if not validate_group_schema(data):
        return jsonify({"error": "Incorrect data structure for Group"}), 400
    result = current_app.db.Groups.update_one({"_id": ObjectId(group_oid)}, {"$set": data})
    if result.matched_count > 0:
        return jsonify({"message": "Group updated successfully"}), 200
    else:
        return jsonify({"error": "Group not found"}), 404


@group_blueprint.route('/group/<string:group_oid>', methods=['DELETE'])
@token_required
def delete_group(group_oid):
    result = current_app.db.Groups.delete_one({"_id": ObjectId(group_oid)})
    if result.deleted_count > 0:
        return jsonify({"message": "Group deleted successfully"}), 200
    else:
        return jsonify({"error": "Group not found"}), 404
