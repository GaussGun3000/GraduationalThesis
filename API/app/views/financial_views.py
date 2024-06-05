from flask import Blueprint, jsonify, request, current_app

from ..auth import token_required
from ..models import Financial, Category, Expense
from dataclasses import asdict
from bson.objectid import ObjectId

financial_blueprint = Blueprint('financial', __name__)


def validate_financial_schema(data: dict) -> Financial | None:
    try:
        oid = data.pop('financial_oid', '-')
        categories = data.pop('categories', [])
        validated_cats = []
        for cat in categories:
            if isinstance(cat, dict):
                validated_exps = []
                expenses = cat.pop("expenses", None)
                for exp in expenses:
                    if isinstance(exp, dict):
                        validated_exp = Expense(**exp)
                        validated_exps.append(validated_exp)
                    elif isinstance(cat, Category):
                        validated_exps.append(exp)
                    else:
                        raise TypeError("Member must be a dict or GroupMember instance")
                validated_cat = Category(expenses=validated_exps, **cat)
                validated_cats.append(validated_cat)
            elif isinstance(cat, Category):
                validated_cats.append(cat)
            else:
                raise TypeError("Category must be a dict or Category instance")
        financial = Financial(financial_oid=oid, categories=validated_cats, **data)
        return financial
    except TypeError as e:
        print(e)
        return None


@financial_blueprint.route('/financial/<string:finance_manager_id>', methods=['GET'])
@token_required
def get_financial(finance_manager_id):
    finance_data = current_app.db.Financial.find_one({"_id": ObjectId(finance_manager_id)})
    if finance_data:
        finance_data['financial_oid'] = str(finance_data['_id'])
        del finance_data['_id']
        finance_manager = Financial(**finance_data)
        return jsonify(asdict(finance_manager))
    else:
        return jsonify({"error": "financial Manager not found"}), 404


@financial_blueprint.route('/financial/user/<string:user_tid>', methods=['GET'])
@token_required
def get_financial_for_user(user_tid):
    user = current_app.db.Users.find_one({"user_tid": int(user_tid)}, {"_id": 1})
    if not user:
        return jsonify({"error": "User not found"}), 404

    user_oid = str(user['_id'])

    # Поиск финансовой информации пользователя
    financial_data = current_app.db.Financial.find_one({"user_oid": user_oid})
    if not financial_data:
        return jsonify({"error": "Financial information not found"}), 404

    financial_data['financial_oid'] = str(financial_data['_id'])
    del financial_data['_id']

    return jsonify(financial_data), 200


@financial_blueprint.route('/financial', methods=['POST'])
@token_required
def create_financial():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 400

    financial = validate_financial_schema(data)
    if not financial:
        return jsonify({"error": "Incorrect data structure for Financial"}), 400

    # finance_manager = Financial(**data)
    finance_manager_id = current_app.db.Financial.insert_one(data).inserted_id
    return jsonify({"financial_oid": str(finance_manager_id)}), 201


@financial_blueprint.route('/financial/<string:financial_oid>/category', methods=['POST'])
@token_required
def add_category_to_financial(financial_oid):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 400

    # Валидация структуры данных категории
    try:
        category = Category(**data)
    except TypeError as e:
        return jsonify({"error": str(e)}), 400

    # Поиск финансового менеджера по OID
    financial_manager = current_app.db.Financial.find_one({"_id": ObjectId(financial_oid)})
    if not financial_manager:
        return jsonify({"error": "Financial manager not found"}), 404

    # Добавление новой категории
    categories = financial_manager.get('categories', [])
    categories.append(asdict(category))

    # Обновление документа в базе данных
    current_app.db.Financial.update_one(
        {"_id": ObjectId(financial_oid)},
        {"$set": {"categories": categories}}
    )

    return jsonify({"message": "Category added successfully"}), 201


@financial_blueprint.route('/financial/<string:financial_oid>/category', methods=['PUT'])
@token_required
def update_category_in_financial(financial_oid):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 400

    old_name = data.get("old_name")
    old_description = data.get("old_description")
    updated_category_data = data.get("updated_category")

    if not old_name or not old_description or not updated_category_data:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        updated_category = Category(**updated_category_data)
    except TypeError as e:
        return jsonify({"error": str(e)}), 400

    financial_manager = current_app.db.Financial.find_one({"_id": ObjectId(financial_oid)})
    if not financial_manager:
        return jsonify({"error": "Financial manager not found"}), 404

    categories = financial_manager.get('categories', [])
    category_found = False
    for category in categories:
        if category['name'] == old_name and category.get('description', '') == old_description:
            category.update(asdict(updated_category))
            category_found = True
            break

    if not category_found:
        return jsonify({"error": "Category not found"}), 404

    current_app.db.Financial.update_one(
        {"_id": ObjectId(financial_oid)},
        {"$set": {"categories": categories}}
    )
    return jsonify({"message": "Category updated successfully"}), 200


@financial_blueprint.route('/financial/<string:financial_oid>/category/expense', methods=['POST'])
@token_required
def add_expense_to_category(financial_oid):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 400

    category_name = data.get("category_name")
    category_description = data.get("category_description")
    expense_data = data.get("expense")
    if not category_name or not category_description or not expense_data:
        return jsonify({"error": "Missing required fields in JSON"}), 400
    try:
        expense = Expense(**expense_data)
    except TypeError as e:
        return jsonify({"error": str(e)}), 400

    financial_manager = current_app.db.Financial.find_one({"_id": ObjectId(financial_oid)})
    if not financial_manager:
        return jsonify({"error": "Financial manager not found"}), 404

    categories = financial_manager.get('categories', [])
    category_found = False

    for category in categories:
        if category['name'] == category_name and category.get('description', '') == category_description:
            category['expenses'].append(asdict(expense))
            category_found = True
            break

    if not category_found:
        return jsonify({"error": "Category not found"}), 404

    # Обновление документа в базе данных
    current_app.db.Financial.update_one(
        {"_id": ObjectId(financial_oid)},
        {"$set": {"categories": categories}}
    )

    return jsonify({"message": "Expense added successfully"}), 201


@financial_blueprint.route('/financial/<string:finance_manager_id>', methods=['PUT'])
@token_required
def update_financial(finance_manager_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 400

    if not validate_financial_schema(data):
        return jsonify({"error": "Incorrect data structure for Financial"}), 400

    result = current_app.db.Financial.update_one({"_id": ObjectId(finance_manager_id)}, {"$set": data})
    if result.matched_count > 0:
        return jsonify({"message": "Financial document updated successfully"}), 200
    else:
        return jsonify({"error": "Financial document not found"}), 404


@financial_blueprint.route('/financial/<string:finance_manager_id>', methods=['DELETE'])
@token_required
def delete_financial(finance_manager_id):
    result = current_app.db.Financial.delete_one({"_id": ObjectId(finance_manager_id)})
    if result.deleted_count > 0:
        return jsonify({"message": "Financial document deleted successfully"}), 200
    else:
        return jsonify({"error": "Financial document not found"}), 404
