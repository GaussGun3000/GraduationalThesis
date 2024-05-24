import requests
from ..config import API_BASE_URL, INTERNAL_API_TOKEN
from datetime import datetime
from ..models import User


HEADERS = {
    "Authorization": f"Bearer {INTERNAL_API_TOKEN}"
}


def get_user_id_list():
    url = f"{API_BASE_URL}/user/tid_list"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get('user_tids', list())  # Предполагается, что API возвращает список ID
    return []


def create_user(user_data):
    url = f"{API_BASE_URL}/user"
    response = requests.post(url, json=user_data, headers=HEADERS)
    return response


def check_and_create_user(user_tid, user_name):
    user_ids = get_user_id_list()
    if user_tid not in user_ids:
        new_user = User(
            user_oid="",
            user_tid=user_tid,
            name=user_name,
            email="",
            status="free",
            registration_date=datetime.now().isoformat(),
            premium_expiry_date="",
            last_active=datetime.now().isoformat(),
            notification_settings={}
        )
        response = create_user(new_user.to_request_dict())
        return response.status_code == 201
    return True
