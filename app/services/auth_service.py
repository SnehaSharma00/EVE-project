from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateUserException, InvalidCredentialsException
from app.core.logging import logger
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenResponse, UserLogin
from app.schemas.user import UserCreate, UserResponse


class AuthService:
    def __init__(self, user_repo: type[UserRepository] = UserRepository):
        self.user_repo = user_repo

    def register_user(self, db: Session, user_in: UserCreate) -> User:
        logger.info(f"Attempting registration for email: {user_in.email.lower().strip()}")
        existing_user = self.user_repo.get_by_email(db, user_in.email)
        if existing_user:
            logger.warning(f"Registration conflict: email '{user_in.email}' already exists")
            raise DuplicateUserException("A user with this email address already exists.")

        password_hash = get_password_hash(user_in.password)
        user = self.user_repo.create(db, user_in, password_hash)
        logger.info(f"User created successfully with id={user.id}")
        return user

    def authenticate_user(self, db: Session, credentials: UserLogin) -> User:
        user = self.user_repo.get_by_email(db, credentials.email)
        if not user:
            logger.warning(f"Auth failed: User '{credentials.email}' not found")
            raise InvalidCredentialsException("Invalid email or password.")

        if not verify_password(credentials.password, user.password_hash):
            logger.warning(f"Auth failed: Incorrect password for user '{credentials.email}'")
            raise InvalidCredentialsException("Invalid email or password.")

        if not user.is_active:
            logger.warning(f"Auth failed: Inactive account for user '{credentials.email}'")
            raise InvalidCredentialsException("User account is inactive.")

        logger.info(f"User id={user.id} authenticated successfully")
        return user

    def create_token_response(self, user: User) -> TokenResponse:
        token_payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
        }
        access_token = create_access_token(token_payload)
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )


auth_service = AuthService()
