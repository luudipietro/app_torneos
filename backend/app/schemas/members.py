from pydantic import BaseModel, Field

from .base import ORM


class MemberIn(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    role: str = Field(default="scorer", pattern="^(scorer|admin)$")


class MemberOut(BaseModel):
    user_id: int
    name: str
    email: str
    role: str


class InvitationOut(ORM):
    id: int
    email: str
    role: str


class MembersOut(BaseModel):
    members: list[MemberOut]
    invitations: list[InvitationOut]


class AssignIn(BaseModel):
    user_ids: list[int]


class BulkAssignIn(BaseModel):
    user_id: int
    match_ids: list[int] = Field(min_length=1, max_length=500)
