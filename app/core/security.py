# app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Any, Union, Optional

from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status # For raising specific HTTP errors

from app.core.config import settings
from app.schemas.token import TokenData # Import TokenData schema

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

def create_access_token(
    subject_id: int, 
    user_email: str, # Keep email for potential full display or other uses
    user_given_name: Optional[str], # Specifically for first name
    expires_delta: Optional[timedelta] = None
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject_id),       # Primary subject: user ID
        "email": user_email,          # Include email
        "given_name": user_given_name or "" # Include given name (first name)
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Function to decode the access token
def decode_access_token(token: str) -> Optional[TokenData]:
    """
    Decodes a JWT access token.
    Returns TokenData if valid, None otherwise or raises HTTPException for specific errors.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        subject: str = payload.get("sub")
        if subject is None:
            # Subject claim is missing
            # We will raise specific HTTPExceptions in the get_current_user dependency
            return None 
        return TokenData(subject=subject)
    except JWTError as e: # Catches expired signature, invalid signature, etc.
        # We will raise specific HTTPExceptions in the get_current_user dependency
        print(f"JWT Error: {e}") # Log the error for debugging
        return None

# Password utilities (for potential future email/password auth)
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)