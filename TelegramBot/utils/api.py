import aiohttp
from ..config import API_BASE_URL, INTERNAL_API_TOKEN
from datetime import datetime
from ..models import User


HEADERS = {
    "Authorization": f"Bearer {INTERNAL_API_TOKEN}"
}


async def get_user_id_list():
    url = f"{API_BASE_URL}/user/tid_list"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('user_tids', list())
            return []


async def create_user(user_data):
    url = f"{API_BASE_URL}/user"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=user_data, headers=HEADERS) as response:
            return response


async def check_and_create_user(user_tid, user_name):
    user_ids = await get_user_id_list()
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
        response = await create_user(new_user.to_request_dict())
        return response.status == 201
    return True


async def get_user_tasks(user_tid):
    url = f"{API_BASE_URL}/task/user/{user_tid}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as response:
            if response.status == 200:
                return await response.json()
            return []
