from typing import List

from app.models import StorageUser
from pydantic import BaseModel


class UserResponse(BaseModel):
    id: int
    email: str
    name: str

    @classmethod
    def from_storage(cls, storage_user: StorageUser):
        return cls(id=storage_user.id, email=storage_user.email, name=storage_user.name)


class ListUsersResponse(BaseModel):
    users: List[UserResponse]

    @classmethod
    def from_storage(cls, storage_users: List[StorageUser]):
        return cls(users=[UserResponse.from_storage(user) for user in storage_users])
