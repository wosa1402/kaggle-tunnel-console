from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    kaggle_username: str
    kaggle_api_key: str
    kernel_slug: str
    tunnel_token: str
    tunnel_url: str = ""


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    kaggle_username: Optional[str] = None
    kaggle_api_key: Optional[str] = None
    kernel_slug: Optional[str] = None
    tunnel_token: Optional[str] = None
    tunnel_url: Optional[str] = None


class AccountOut(BaseModel):
    id: int
    name: str
    kaggle_username: str
    kernel_slug: str
    tunnel_url: str
    last_status: str
    last_run_at: Optional[datetime]

    class Config:
        from_attributes = True
