# app/schemas/user.py
from pydantic import BaseModel, EmailStr
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    display_name: Optional[str] = None
    # You might add is_active, is_superuser later

class UserCreate(UserBase):
    oauth_provider: Optional[str] = None # e.g., "google"
    oauth_id: Optional[str] = None       # Google's subject ID
    # For password auth: password: str 

class UserUpdate(UserBase):
    pass # Define fields that can be updated

class UserInDBBase(UserBase):
    id: int
    oauth_provider: Optional[str] = None
    oauth_id: Optional[str] = None
    
    class Config:
        from_attributes = True

class User(UserInDBBase): # Schema for returning user info via API
    pass

class UserInDB(UserInDBBase): # Schema for user object stored in DB (internal)
    pass