"""Users API routes."""
from app.models import user as user_model
from app.schemas.user import User
from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=list[User], summary="List users")
def list_users():
    """Return all users (single-user system, usually one row)."""
    return user_model.get_all_users()


@router.get("/{user_id}", response_model=User, summary="Get the user (name + cash balance)")
def get_user(user_id: int):
    """Return a single user by id."""
    row = user_model.get_user_by_id(user_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    return row
