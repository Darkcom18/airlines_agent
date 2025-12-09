"""
Authentication routes for C1 Travel Agent System.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.db.database import get_db
from src.db.models import User
from src.auth.password import hash_password, verify_password
from src.auth.jwt import create_access_token, get_current_user
from src.auth.schemas import (
    UserCreate, UserLogin, UserResponse, TokenResponse, TokenData
)
from src.cache import get_redis, RedisCache

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user."""
    # Check if email exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    new_user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Generate token
    token = create_access_token(new_user.id, new_user.email)

    # Cache token in Redis
    try:
        redis_client = await get_redis()
        cache = RedisCache(redis_client)
        await cache.cache_jwt(str(new_user.id), token)
    except Exception:
        pass  # Redis not available, continue without caching

    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(new_user)
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Login and get access token."""
    # Find user
    result = await db.execute(
        select(User).where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )

    # Generate token
    token = create_access_token(user.id, user.email)

    # Cache token in Redis
    try:
        redis_client = await get_redis()
        cache = RedisCache(redis_client)
        await cache.cache_jwt(str(user.id), token)
    except Exception:
        pass

    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user)
    )


@router.post("/logout")
async def logout(
    current_user: TokenData = Depends(get_current_user)
):
    """Logout and invalidate token."""
    try:
        redis_client = await get_redis()
        cache = RedisCache(redis_client)
        await cache.invalidate_jwt(str(current_user.user_id))
    except Exception:
        pass

    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user info."""
    result = await db.execute(
        select(User).where(User.id == current_user.user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse.model_validate(user)
