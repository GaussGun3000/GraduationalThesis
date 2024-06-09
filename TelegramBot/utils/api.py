from dataclasses import asdict
from typing import Tuple

import aiohttp
from ..config import API_BASE_URL, INTERNAL_API_TOKEN
from datetime import datetime, timezone
from ..models import User, Task, Category, Expense, Financial, Group, GroupMember

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


async def get_user(user_tid: int) -> User | None:
    url = f"{API_BASE_URL}/user/{user_tid}"
    async with session.get(url, headers=HEADERS) as response:
        if response.status == 200:
            data = await response.json()
            return User(**data)
        return None


async def create_user(user_data: dict):
    url = f"{API_BASE_URL}/user"
    async with session.post(url, json=user_data, headers=HEADERS) as response:
        return response


async def check_and_create_user(user_tid, user_name):
    user_ids = await get_user_id_list()
    current_date = datetime.now(timezone.utc).isoformat()
    if user_tid not in user_ids:
        new_user = User(
            user_oid="",
            user_tid=user_tid,
            name=user_name,
            email="",
            status="free",
            registration_date=current_date,
            premium_expiry_date="",
            last_active=current_date,
            notification_settings={}
        )
        response = await create_user(new_user.to_request_dict())
        if response.status == 201:
            data = await response.json()
            return data.get('user_oid')
        else:
            return None
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


async def get_financial_info(user_id: int) -> Financial | None:
    url = f"{API_BASE_URL}/financial/user/{user_id}"
    async with session.get(url, headers=HEADERS) as response:
        if response.status == 200:
            data = await response.json()
            if not data:
                return None
            categories = [Category(
                category_id=category['category_id'],
                name=category['name'],
                description=category['description'],
                budget_limit=category['budget_limit'],
                expenses=[Expense(**expense) for expense in category['expenses']]
            ) for category in data['categories']]
            return Financial(
                financial_oid=data['financial_oid'],
                categories=categories,
                reset_day=data['reset_day'],
                group_oid=data.get('group_oid', ''),
                user_oid=data.get('user_oid', '')
            )
        else:
            return None


async def create_financial(fin: Financial) -> str | None:
    url = f"{API_BASE_URL}/financial"
    async with session.post(url, json=fin.to_request_dict(), headers=HEADERS) as response:
        data = await response.json()
        if not data:
            return None
        return data.get('financial_oid')


async def update_reset_day(financial: Financial, reset_day: int) -> bool:
    url = f"{API_BASE_URL}/financial/{financial.financial_oid}"
    financial.reset_day = reset_day
    async with session.put(url, json=financial.to_request_dict(), headers=HEADERS) as response:
        return response.status == 200


async def create_category(financial: Financial, category: Category) -> bool:
    url = f"{API_BASE_URL}/financial/{financial.financial_oid}/category"
    data = category.to_request_dict()
    async with session.post(url, json=data, headers=HEADERS) as response:
        return response.status == 201


async def update_category(financial_info: Financial, old_name: str, old_description: str, updated_category: Category) -> bool:
    url = f"{API_BASE_URL}/financial/{financial_info.financial_oid}/category"
    data = {
        "old_name": old_name,
        "old_description": old_description,
        "updated_category": updated_category.to_request_dict()
    }
    async with session.put(url, json=data, headers=HEADERS) as response:
        return response.status == 200


async def create_expense(financial_oid: str, category: Category, expense: Expense) -> bool:
    url = f"{API_BASE_URL}/financial/{financial_oid}/category/expense"
    data = {
        "category_name": category.name,
        "category_description": category.description,
        "expense": expense.to_request_dict()
    }
    async with session.post(url, json=data, headers=HEADERS) as response:
        return response.status == 201


async def get_created_group(user_tid: int):
    url = f"{API_BASE_URL}/group/user/{user_tid}/created"
    async with session.get(url, headers=HEADERS) as response:
        if response.status == 200:
            data = await response.json()
            return data.get('created_group')
        return None


async def get_user_groups(user_tid: int):
    url = f"{API_BASE_URL}/group/user/{user_tid}"
    async with session.get(url, headers=HEADERS) as response:
        if response.status == 200:
            return await response.json()
        return None


async def get_group(group_oid: str):
    url = f"{API_BASE_URL}/group/{group_oid}"
    async with session.get(url, headers=HEADERS) as response:
        if response.status == 200:
            data = await response.json()
            members = [GroupMember(**member_data) for member_data in data['members']]
            return Group(
                group_oid=data['group_oid'],
                name=data['name'],
                description=data['description'],
                members=members
            )
        return None


async def create_group(group: Group) -> Tuple[bool, str]:
    url = f"{API_BASE_URL}/group"
    async with session.post(url, json=group.to_request_dict(), headers=HEADERS) as response:
        data = await response.json()
        return response.status == 201, data.get('group_oid')


async def add_group_member(group_oid: str, member: GroupMember) -> bool:
    url = f"{API_BASE_URL}/group/{group_oid}/member"
    data = {"member": member.to_request_dict()}
    async with session.post(url, json=data, headers=HEADERS) as response:
        return response.status == 201


async def update_group(group: Group) -> bool:
    url = f"{API_BASE_URL}/group/{group.group_oid}"
    data = group.to_request_dict()
    async with session.put(url, json=data, headers=HEADERS) as response:
        return response.status == 200


async def update_group_members(group: Group) -> bool:
    url = f"{API_BASE_URL}/group/{group.group_oid}/members"
    data = {"members": [member.to_request_dict() for member in group.members]}
    async with session.put(url, json=data, headers=HEADERS) as response:
        return response.status == 200


async def set_member_role(group_oid: str, member: GroupMember) -> bool:
    url = f"{API_BASE_URL}/group/{group_oid}/set_member_role"
    data = {
        "user_tid": member.member_tid,
        "new_role": member.role
    }
    async with session.put(url, json=data, headers=HEADERS) as response:
        return response.status == 200


async def get_group_tasks(group_oid: str):
    url = f"{API_BASE_URL}/task/group/{group_oid}"
    async with session.get(url, headers=HEADERS) as response:
        if response.status == 200:
            data = await response.json()
            tasks = list()
            for item in data:
                item['task_oid'] = item.pop("_id")
                tasks.append(Task(**item))
            return tasks
        return None


async def close_session():
    await session.close()
