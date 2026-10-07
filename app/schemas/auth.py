from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """User credentials for authentication."""

    email: str = Field(..., description="Registered user email address")
    password: str = Field(..., min_length=1, description="Account password")


class UserOut(BaseModel):
    """Authenticated user public profile."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    target_role: Optional[str] = "Python Backend Engineer"
    is_active: bool = True



class TokenResponse(BaseModel):
    """JWT bearer token and authenticated user payload."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400
    user: UserOut
