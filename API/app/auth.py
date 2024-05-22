from flask import request, jsonify, current_app
from functools import wraps


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token is missing!"}), 401
        if token not in current_app.config['AUTHORIZED_TOKENS']:
            return jsonify({"error": "Unauthorized access!"}), 403
        return f(*args, **kwargs)
    return decorated
