"""
User management routes for C1 Travel Agent System.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from datetime import date

from src.db.database import get_db
from src.db.models import User, UserPassenger, UserFFCard
from src.auth.jwt import get_current_user
from src.auth.schemas import TokenData, UserResponse

router = APIRouter(prefix="/user", tags=["User Management"])


# ============ Schemas ============

class PassengerCreate(BaseModel):
    """Schema for creating a passenger."""
    passenger_type: str = Field(default="ADT", pattern="^(ADT|CHD|INF)$")
    title: Optional[str] = Field(None, pattern="^(Mr|Mrs|Ms|Mstr|Miss)$")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, pattern="^(M|F)$")
    nationality: Optional[str] = Field(None, max_length=3)
    passport_number: Optional[str] = Field(None, max_length=50)
    passport_expiry: Optional[date] = None
    passport_country: Optional[str] = Field(None, max_length=3)
    is_default: bool = False


class PassengerResponse(PassengerCreate):
    """Schema for passenger response."""
    id: UUID

    class Config:
        from_attributes = True


class PassengerUpdate(BaseModel):
    """Schema for updating a passenger."""
    title: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    nationality: Optional[str] = None
    passport_number: Optional[str] = None
    passport_expiry: Optional[date] = None
    passport_country: Optional[str] = None
    is_default: Optional[bool] = None


class FFCardCreate(BaseModel):
    """Schema for creating a frequent flyer card."""
    airline_code: str = Field(..., min_length=2, max_length=3)
    card_number: str = Field(..., min_length=1, max_length=50)
    card_type: Optional[str] = None


class FFCardResponse(FFCardCreate):
    """Schema for FF card response."""
    id: UUID

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    """Schema for updating user profile."""
    full_name: Optional[str] = None
    phone: Optional[str] = None


# ============ Profile Routes ============

@router.get("/profile", response_model=UserResponse)
async def get_profile(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user profile."""
    result = await db.execute(
        select(User).where(User.id == current_user.user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse.model_validate(user)


@router.patch("/profile", response_model=UserResponse)
async def update_profile(
    data: ProfileUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user profile."""
    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")

    await db.execute(
        update(User)
        .where(User.id == current_user.user_id)
        .values(**update_data)
    )
    await db.commit()

    result = await db.execute(
        select(User).where(User.id == current_user.user_id)
    )
    user = result.scalar_one()

    return UserResponse.model_validate(user)


# ============ Passenger Routes ============

@router.get("/passengers", response_model=List[PassengerResponse])
async def list_passengers(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all saved passengers for current user."""
    result = await db.execute(
        select(UserPassenger)
        .where(UserPassenger.user_id == current_user.user_id)
        .order_by(UserPassenger.is_default.desc(), UserPassenger.created_at)
    )
    passengers = result.scalars().all()

    return [PassengerResponse.model_validate(p) for p in passengers]


@router.post("/passengers", response_model=PassengerResponse, status_code=201)
async def create_passenger(
    data: PassengerCreate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new saved passenger."""
    # If setting as default, unset other defaults
    if data.is_default:
        await db.execute(
            update(UserPassenger)
            .where(UserPassenger.user_id == current_user.user_id)
            .values(is_default=False)
        )

    passenger = UserPassenger(
        user_id=current_user.user_id,
        **data.model_dump()
    )

    db.add(passenger)
    await db.commit()
    await db.refresh(passenger)

    return PassengerResponse.model_validate(passenger)


@router.get("/passengers/{passenger_id}", response_model=PassengerResponse)
async def get_passenger(
    passenger_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific passenger."""
    result = await db.execute(
        select(UserPassenger)
        .where(
            UserPassenger.id == passenger_id,
            UserPassenger.user_id == current_user.user_id
        )
    )
    passenger = result.scalar_one_or_none()

    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger not found")

    return PassengerResponse.model_validate(passenger)


@router.patch("/passengers/{passenger_id}", response_model=PassengerResponse)
async def update_passenger(
    passenger_id: UUID,
    data: PassengerUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a passenger."""
    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")

    # If setting as default, unset others
    if update_data.get("is_default"):
        await db.execute(
            update(UserPassenger)
            .where(UserPassenger.user_id == current_user.user_id)
            .values(is_default=False)
        )

    result = await db.execute(
        update(UserPassenger)
        .where(
            UserPassenger.id == passenger_id,
            UserPassenger.user_id == current_user.user_id
        )
        .values(**update_data)
        .returning(UserPassenger)
    )
    passenger = result.scalar_one_or_none()

    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger not found")

    await db.commit()
    return PassengerResponse.model_validate(passenger)


@router.delete("/passengers/{passenger_id}", status_code=204)
async def delete_passenger(
    passenger_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a passenger."""
    result = await db.execute(
        delete(UserPassenger)
        .where(
            UserPassenger.id == passenger_id,
            UserPassenger.user_id == current_user.user_id
        )
    )

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Passenger not found")

    await db.commit()


# ============ Frequent Flyer Routes ============

@router.get("/ff-cards", response_model=List[FFCardResponse])
async def list_ff_cards(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all frequent flyer cards."""
    result = await db.execute(
        select(UserFFCard)
        .where(UserFFCard.user_id == current_user.user_id)
        .order_by(UserFFCard.airline_code)
    )
    cards = result.scalars().all()

    return [FFCardResponse.model_validate(c) for c in cards]


@router.post("/ff-cards", response_model=FFCardResponse, status_code=201)
async def create_ff_card(
    data: FFCardCreate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a frequent flyer card."""
    # Check for duplicate
    result = await db.execute(
        select(UserFFCard)
        .where(
            UserFFCard.user_id == current_user.user_id,
            UserFFCard.airline_code == data.airline_code,
            UserFFCard.card_number == data.card_number
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Card already exists")

    card = UserFFCard(
        user_id=current_user.user_id,
        **data.model_dump()
    )

    db.add(card)
    await db.commit()
    await db.refresh(card)

    return FFCardResponse.model_validate(card)


@router.delete("/ff-cards/{card_id}", status_code=204)
async def delete_ff_card(
    card_id: UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a frequent flyer card."""
    result = await db.execute(
        delete(UserFFCard)
        .where(
            UserFFCard.id == card_id,
            UserFFCard.user_id == current_user.user_id
        )
    )

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Card not found")

    await db.commit()
