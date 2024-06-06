from dataclasses import dataclass, field, asdict
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
    notification_settings: Dict[str, bool] = field(default_factory=dict)

    def to_request_dict(self):
        data = asdict(self)
        data.pop('user_oid')
        return data

    def is_premium(self):
        return self.status == "premium"


@dataclass
class Group:
    group_oid: str
    name: str
    description: str = "No description"
    members: List['GroupMember'] = field(default_factory=list)

    def to_request_dict(self):
        data = asdict(self)
        data.pop('group_oid')
        return data


@dataclass
class GroupMember:
    role: str
    permissions: Dict
    member_oid: str
    member_tid: int

    def to_request_dict(self):
        data = asdict(self)
        return data


@dataclass
class Task:
    task_oid: str
    group_oid: str
    title: str
    description: str
    status: str
    creator_oid: str
    assigned_to: List[str]
    deadline: str
    last_updated: str
    recurring: str
    completion_date: str = ""

    def to_request_dict(self):
        data = asdict(self)
        data.pop('task_oid')
        return data


@dataclass
class Financial:
    financial_oid: str
    categories: List['Category']
    reset_day: str
    group_oid: str = ""
    user_oid: str = ""

    def to_request_dict(self):
        data = asdict(self)
        data.pop('financial_oid')
        return data


@dataclass
class Category:
    category_id: str  # optional?
    name: str
    description: str
    budget_limit: float
    expenses: List['Expense']

    def to_request_dict(self):
        data = asdict(self)
        return data


@dataclass
class Expense:
    expense_id: str  # optional?
    amount: float
    description: str
    date: str
    user_oid: str

    def to_request_dict(self):
        data = asdict(self)
        return data

