from pydantic import BaseModel, EmailStr, Field
from typing import Dict, List


class UserSchema(BaseModel):
    user_oid: str
    user_tid: int
    name: str
    email: EmailStr
    status: str
    registration_date: str
    premium_expiry_date: str
    last_active: str
    notification_settings: Dict[str, bool]


class GroupMemberSchema(BaseModel):
    role: str
    permissions: Dict
    member_oid: str
    member_tid: int


class GroupSchema(BaseModel):
    group_oid: str
    name: str
    description: str
    members: List[GroupMemberSchema]


class TaskSchema(BaseModel):
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


class ExpenseSchema(BaseModel):
    amount: float
    description: str
    date: str
    user_oid: str


class CategorySchema(BaseModel):
    name: str
    budget_limit: float
    expenses: List[ExpenseSchema]


class FinanceManagerSchema(BaseModel):
    group_oid: str
    categories: List[CategorySchema]
    reset_date: str
