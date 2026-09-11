from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_user,
    require_role,
)
from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import Token
from app.schemas.user import UserRegister, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(
    user_in: UserRegister,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Register a new user with email, password, and supported role."""
    # Check if email is already registered
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    # Hash the password and create the user
    hashed_pwd = get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        hashed_password=hashed_pwd,
        role=user_in.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    summary="OAuth2-compatible login to obtain JWT access token",
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """Authenticate user with username (email) and password, returning a Bearer JWT."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
        }
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    return UserResponse.model_validate(current_user)


# =====================================================================
# Role Protection Test Endpoints (for verification of RBAC boundaries)
# =====================================================================

@router.get(
    "/test/shopkeeper",
    summary="Test endpoint requiring shopkeeper role",
)
def test_shopkeeper(
    current_user: User = Depends(require_role("shopkeeper")),
):
    return {
        "message": "Access granted: Shopkeeper",
        "user_id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
    }


@router.get(
    "/test/shopper",
    summary="Test endpoint requiring shopper role",
)
def test_shopper(
    current_user: User = Depends(require_role("shopper")),
):
    return {
        "message": "Access granted: Shopper",
        "user_id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
    }


@router.get(
    "/test/counter",
    summary="Test endpoint requiring counter role",
)
def test_counter(
    current_user: User = Depends(require_role("counter")),
):
    return {
        "message": "Access granted: Counter Staff",
        "user_id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
    }
