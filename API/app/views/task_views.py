from datetime import datetime

from flask import Blueprint, jsonify, request, current_app

from ..auth import token_required
from ..models import Task
from dataclasses import asdict
from bson.objectid import ObjectId

task_blueprint = Blueprint('task', __name__)


def validate_task_schema(data: dict) -> Task | None:
    try:
        oid = data.pop('task_oid', '-')
        task = Task(task_oid=oid, **data)
        return task
    except TypeError as e:
        print(e)
        return None


@task_blueprint.route('/task/<string:task_oid>', methods=['GET'])
@token_required
def get_task_by_oid(task_oid):
    task_data = current_app.db.Tasks.find_one({"_id": ObjectId(task_oid)})
    if task_data:
        task_data['task_oid'] = str(task_data['_id'])
        del task_data['_id']
        task = Task(**task_data)
        return jsonify(asdict(task))
    else:
        return jsonify({"error": "Task not found"}), 404


@task_blueprint.route('/task/user/<int:user_tid>', methods=['GET'])
@token_required
def get_tasks_by_user_tid(user_tid):
    # Поиск пользователя по user_tid
    user = current_app.db.Users.find_one({"user_tid": user_tid}, {"_id": 1})
    if not user:
        return jsonify({"error": "User not found"}), 404

    user_oid = str(user['_id'])

    # Поиск задач, где пользователь указан как исполнитель
    tasks = list(current_app.db.Tasks.find({"assigned_to": user_oid}))
    for task in tasks:
        task['task_oid'] = str(task['_id'])
        del task['_id']
    return jsonify(tasks), 200


@task_blueprint.route('/task/group/<string:group_oid>', methods=['GET'])
@token_required
def get_tasks_by_group(group_oid):
    group = current_app.db.Groups.find_one({"_id": ObjectId(group_oid)})
    if not group:
        return jsonify({"error": "Group not found"}), 404

    tasks = current_app.db.Tasks.find({"group_oid": group_oid})
    task_list = []
    for task in tasks:
        task["_id"] = str(task["_id"])
        task_list.append(task)

    return jsonify(task_list), 200


@task_blueprint.route('/task/active', methods=['GET'])
@token_required
def get_active_tasks():
    tasks = current_app.db.Tasks.find({"status": "open"})
    task_list = []
    for task in tasks:
        task["_id"] = str(task["_id"])
        task_list.append(task)

    return jsonify(task_list), 200


@task_blueprint.route('/task', methods=['POST'])
@token_required
def create_task():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 400

    task = validate_task_schema(data)
    if not task:
        return jsonify({"error": "Incorrect data structure for Task"}), 400
    task_dict = asdict(task)
    task_dict.pop('task_oid', None)

    task_id = current_app.db.Tasks.insert_one(task_dict).inserted_id
    return jsonify({"task_oid": str(task_id)}), 201


@task_blueprint.route('/task/<string:task_oid>', methods=['PUT'])
@token_required
def update_task(task_oid):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 400

    if not validate_task_schema(data):
        return jsonify({"error": "Incorrect data structure for Task"}), 400

    result = current_app.db.Tasks.update_one({"_id": ObjectId(task_oid)}, {"$set": data})
    if result.matched_count > 0:
        return jsonify({"message": "Task updated successfully"}), 200
    else:
        return jsonify({"error": "Task not found"}), 404


@task_blueprint.route('/task/<string:task_oid>', methods=['DELETE'])
@token_required
def delete_task(task_oid):
    result = current_app.db.Tasks.delete_one({"_id": ObjectId(task_oid)})
    if result.deleted_count > 0:
        return jsonify({"message": "Task deleted successfully"}), 200
    else:
        return jsonify({"error": "Task not found"}), 404
