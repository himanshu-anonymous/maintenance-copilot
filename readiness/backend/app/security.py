import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import bcrypt

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db_session, Base, engine
from app.workflow.models import User, Asset
from app.graph.json_store import graph_store

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


def require_role(allowed_roles: List[str]):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Requires role in: {allowed_roles}"
            )
        return current_user
    return role_checker


async def init_db():
    """Create database tables and seed initial demo users and assets."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        # 1. Seed demo users
        demo_users = [
            {
                "id": "usr-tech-01",
                "username": "tech",
                "password": settings.DEMO_TECH_PASSWORD,
                "role": "technician",
                "full_name": "Alex Vance (Field Technician)"
            },
            {
                "id": "usr-super-01",
                "username": "supervisor",
                "password": settings.DEMO_SUPERVISOR_PASSWORD,
                "role": "supervisor",
                "full_name": "Elena Rostova (Plant Reliability Supervisor)"
            }
        ]

        for u in demo_users:
            stmt = select(User).where(User.username == u["username"])
            res = await session.execute(stmt)
            existing = res.scalar_one_or_none()
            if not existing:
                new_user = User(
                    id=u["id"],
                    username=u["username"],
                    password_hash=get_password_hash(u["password"]),
                    role=u["role"],
                    full_name=u["full_name"],
                    created_at=datetime.utcnow()
                )
                session.add(new_user)
                logger.info(f"Seeded demo user: {u['username']} ({u['role']})")

        # 2. Seed assets from graph store (or fallback to knowledge/assets.json)
        equipment_nodes = graph_store.get_nodes("Equipment")
        if not equipment_nodes:
            for p in ["/app/knowledge/assets.json", "knowledge/assets.json", "../knowledge/assets.json"]:
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        equipment_nodes = json.load(f)
                        break
                except Exception:
                    pass

        for eq in equipment_nodes:
            stmt = select(Asset).where(Asset.id == eq["id"])
            res = await session.execute(stmt)
            existing_asset = res.scalar_one_or_none()
            if not existing_asset:
                new_asset = Asset(
                    id=eq["id"],
                    tag=eq.get("tag", eq["id"]),
                    name=eq.get("name", eq["id"]),
                    category=eq.get("category", "equipment"),
                    model=eq.get("model", "standard"),
                    serial_number=eq.get("serial_number", f"SN-{eq['id']}"),
                    manual_revision=eq.get("manual_revision", "Rev A"),
                    location=eq.get("location", "Bay 1"),
                    critical_rating=eq.get("critical_rating", "B"),
                    last_inspection_date=eq.get("last_inspection_date", "2026-01-15"),
                    status=eq.get("status", "operational"),
                    created_at=datetime.utcnow()
                )
                session.add(new_asset)
                logger.info(f"Seeded asset: {eq['id']} - {new_asset.name}")

        await session.commit()
