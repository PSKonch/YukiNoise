from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = None


class UserRead(UserBase):
    id: UUID
    role: str
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class User(UserRead):
    pass
