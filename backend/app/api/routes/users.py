from fastapi import APIRouter, Depends, HTTPException
from typing import Any
from app.api.deps import SessionDep, get_current_active_user
from app.schemas.user import User, UserCreate
from app.db.models import User as UserModel
from app.core.security import get_password_hash

router = APIRouter()

@router.post("/", response_model=User)
def create_user(
    *,
    db: SessionDep,
    user_in: UserCreate,
) -> Any:
    """
    Create new user.
    """
    user = db.query(UserModel).filter(UserModel.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    user_obj = UserModel(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role
    )
    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)
    return user_obj

@router.get("/me", response_model=User)
def read_user_me(
    current_user: UserModel = Depends(get_current_active_user)
) -> Any:
    """
    Get current user.
    """
    return current_user
