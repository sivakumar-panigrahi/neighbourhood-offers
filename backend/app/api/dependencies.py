from typing import Callable, Sequence

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate Bearer token and fetch authenticated user from database."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.InvalidTokenError, jwt.PyJWTError):
        raise credentials_exception

    # Query user from DB (support both integer ID string and email string in sub)
    user: User | None = None
    if user_id_str.isdigit():
        user = db.query(User).filter(User.id == int(user_id_str)).first()
    if user is None:
        user = db.query(User).filter(User.email == user_id_str).first()

    if user is None:
        raise credentials_exception

    return user


def require_role(required_role: str) -> Callable[[User], User]:
    """Dependency factory ensuring user has the specific role."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role: '{required_role}'",
            )
        return current_user

    return role_checker


def require_roles(*required_roles: str) -> Callable[[User], User]:
    """Dependency factory ensuring user has one of the specified roles."""
    def roles_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required one of roles: {list(required_roles)}",
            )
        return current_user

    return roles_checker


def get_current_shopkeeper(
    current_user: User = Depends(require_role("shopkeeper")),
) -> User:
    """Dependency ensuring current user is a shopkeeper."""
    return current_user


def get_current_shopper(
    current_user: User = Depends(require_role("shopper")),
) -> User:
    """Dependency ensuring current user is a shopper."""
    return current_user


def get_current_counter(
    current_user: User = Depends(require_role("counter")),
) -> User:
    """Dependency ensuring current user is counter staff."""
    return current_user


def verify_shop_owner(shop: object, current_user: User) -> None:
    """Verify that the current user owns the specified shop."""
    owner_id = getattr(shop, "owner_id", None)
    if owner_id is None or owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this shop",
        )
