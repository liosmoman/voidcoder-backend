# app/crud/crud_user.py
from sqlalchemy.orm import Session
from typing import Optional

from app.crud.crud_base import CRUDBase
from app.models.prompt_session import User # Your SQLAlchemy User model
from app.schemas.user import UserCreate, UserUpdate # Your Pydantic User schemas

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def get_by_oauth_id(self, db: Session, *, oauth_provider: str, oauth_id: str) -> Optional[User]:
        return db.query(User).filter(User.oauth_provider == oauth_provider, User.oauth_id == oauth_id).first()

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        # In a real app, if supporting passwords, you'd hash password here before saving
        db_obj = User(
            email=obj_in.email,
            display_name=obj_in.display_name,
            oauth_provider=obj_in.oauth_provider,
            oauth_id=obj_in.oauth_id
            # hashed_password=get_password_hash(obj_in.password) # If using passwords
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # You can add update methods, is_superuser checks, etc. later

user = CRUDUser(User)