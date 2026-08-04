"""Users API routes."""
from app.models import user as user_model
from app.routers.utils import require_user_exists
from app.schemas.user import User
from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=list[User], summary="List users")
def list_users():
    """Return all users (single-user system, usually one row)."""
    return user_model.get_all_users()


@router.get("/{user_id}", response_model=User, summary="Get the user (name + cash balance)")
@require_user_exists
def get_user(user_id: int):
    """Return a single user by id."""
    return user_model.get_user_by_id(user_id)
