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
    return jsonify({"finance_manager_id": str(finance_manager_id)}), 201


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
