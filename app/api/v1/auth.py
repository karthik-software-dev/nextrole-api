from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.deps import get_current_user, get_db_session
from config import ACCESS_TOKEN_EXPIRE_MINUTES
from core.security import create_access_token, verify_password
from schemas.auth import LoginRequest, TokenResponse, UserOut
from storage.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User Login",
    description="Authenticates candidate or admin credentials and issues a signed JWT access token.",
)
def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db_session),
) -> TokenResponse:
    email = credentials.email.strip().lower()
    user = db.query(User).filter(User.email.ilike(email)).first()

    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is currently inactive. Please contact system administrator.",
        )

    access_token = create_access_token(
        data={"sub": user.email, "uid": user.id, "name": user.name}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get Current User Profile",
    description="Returns public profile and role of the currently authenticated JWT bearer.",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserOut:
    return UserOut.model_validate(current_user)


@router.post(
    "/logout",
    summary="User Logout",
    description="Client clears stored token. Endpoint provides standard acknowledgement.",
)
def logout() -> dict[str, str]:
    return {"message": "Logged out successfully"}
