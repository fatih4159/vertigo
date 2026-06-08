from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.core.security import verify_password, get_password_hash, create_access_token
from app.schemas.auth import TokenResponse
from app.schemas.user import UserCreate
from loguru import logger


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate(self, email: str, password: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user

    async def create_token(self, user: User) -> TokenResponse:
        token = create_access_token(str(user.id))
        return TokenResponse(access_token=token)

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        import uuid
        try:
            uid = uuid.UUID(user_id)
        except ValueError:
            return None
        result = await self.db.execute(select(User).where(User.id == uid))
        return result.scalar_one_or_none()

    async def create_user(self, user_in: UserCreate) -> User:
        hashed = get_password_hash(user_in.password)
        user = User(
            email=user_in.email,
            hashed_password=hashed,
            full_name=user_in.full_name,
            role=user_in.role,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        logger.info(f"Created user: {user.email} role={user.role}")
        return user

    async def ensure_default_admin(self) -> None:
        result = await self.db.execute(select(User))
        users = result.scalars().all()
        if not users:
            from app.models.user import UserRole
            admin = User(
                email="admin@cynefa.com",
                hashed_password=get_password_hash("admin123"),
                full_name="System Admin",
                role=UserRole.ADMIN,
                is_active=True,
            )
            self.db.add(admin)
            await self.db.flush()
            logger.warning("Created default admin user: admin@cynefa.com / admin123 - CHANGE IMMEDIATELY")
