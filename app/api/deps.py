from collections.abc import Callable

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ForbiddenException,
    InvalidTokenException,
    TokenExpiredException,
)
from app.db.database import get_db
from app.db.models.enums import UserRole
from app.db.models.user import User
from app.repositories.user_repository import UserRepository

security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    auth_header: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not auth_header or not auth_header.credentials:
        raise InvalidTokenException("Missing or malformed Authorization header.")

    token = auth_header.credentials
    try:
        from app.core.security import decode_access_token

        payload = decode_access_token(token)
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise InvalidTokenException("Token payload missing subject.")
        user_id = int(user_id_str)
    except jwt.ExpiredSignatureError as err:
        raise TokenExpiredException("Authentication token has expired.") from err
    except (jwt.PyJWTError, ValueError) as err:
        raise InvalidTokenException("Invalid or corrupted authentication token.") from err

    user = UserRepository.get_by_id(db, user_id=user_id)
    if not user:
        raise InvalidTokenException("User associated with this token no longer exists.")

    if not user.is_active:
        raise ForbiddenException("User account is inactive.")

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise ForbiddenException("User account is inactive.")
    return current_user


def require_role(*roles: UserRole) -> Callable[[User], User]:
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in roles:
            raise ForbiddenException(
                f"Action requires one of the following roles: {[r.value for r in roles]}"
            )
        return current_user

    return role_checker
