from dataclasses import asdict

import aiohttp
from ..config import API_BASE_URL, INTERNAL_API_TOKEN
from datetime import datetime
from ..models import User, Task

HEADERS = {
    "Authorization": f"Bearer {INTERNAL_API_TOKEN}"
}

timeout = aiohttp.ClientTimeout(total=10)
session = aiohttp.ClientSession(timeout=timeout)


async def get_user_id_list():
    url = f"{API_BASE_URL}/user/tid_list"
    async with session.get(url, headers=HEADERS) as response:
        if response.status == 200:
            data = await response.json()
            return data.get('user_tids', list())
        return []


async def get_user(user_tid: int) -> User:
    url = f"{API_BASE_URL}/user/{user_tid}"
    async with session.get(url, headers=HEADERS) as response:
        if response.status == 200:
            data = await response.json()
            return User(**data)
        return []


async def create_user(user_data):
    url = f"{API_BASE_URL}/user"
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
    async with session.get(url, headers=HEADERS) as response:
        if response.status == 200:
            tasks_data = await response.json()
            tasks = []
            for task_data in tasks_data:
                tasks.append(Task(**task_data))
            return tasks
        return []


async def is_group_admin(user_tid, group_oid) -> bool:
    url = f"{API_BASE_URL}/group/{group_oid}/admins"
    async with session.get(url, headers=HEADERS) as response:
        if response.status == 200:
            admins = await response.json()
            return any(admin['user_tid'] == user_tid for admin in admins)
        return False


async def update_task(task_oid, updated: Task):
    url = f"{API_BASE_URL}/task/{task_oid}"
    async with session.put(url, json=updated.to_request_dict(), headers=HEADERS) as response:
        return response.status == 200


async def create_task(task: Task):
    url = f"{API_BASE_URL}/task"
    async with session.post(url, json=task.to_request_dict(), headers=HEADERS) as response:
        return response


async def delete_task(task_oid: str) -> bool:
    url = f"{API_BASE_URL}/task/{task_oid}"
    async with session.delete(url, headers=HEADERS) as response:
        return response.status == 200


async def close_session():
    await session.close()