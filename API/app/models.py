from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class User:
    user_oid: str
    user_tid: int
    name: str
    email: str
    status: str
    registration_date: str
    premium_expiry_date: str
    last_active: str
    notification_settings: Dict[str, bool]


@dataclass
class Group:
    group_oid: str
    name: str
    description: str
    members: List['GroupMember']


@dataclass
class GroupMember:
    role: str
    permissions: Dict
    member_oid: str
    member_tid: int


@dataclass
class Task:
    task_oid: str
    group_oid: str
    title: str
    description: str
    status: str
    creator_id: str
    assigned_to: List[str]
    due_date: str
    last_updated: str
    recurring: str
    completion_date: str


@dataclass
class FinanceManager:
    finance_manager_id: str
    group_oid: str
    categories: List['Category']
    reset_date: str


@dataclass
class Category:
    category_id: str  # optional?
    name: str
    budget_limit: float
    expenses: List['Expense']


@dataclass
class Expense:
    expense_id: str  # optional?
    amount: float
    description: str
    date: str
    user_oid: str

