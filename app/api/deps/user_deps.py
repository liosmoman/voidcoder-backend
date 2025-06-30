# app/api/deps/user_deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer # Standard way to get Bearer token
from sqlalchemy.orm import Session
from jose import JWTError # For catching JWT specific errors if needed beyond what decode_access_token handles

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.prompt_session import User as UserModel # SQLAlchemy User model
from app.schemas.token import TokenData
from app.crud.crud_user import user as crud_user # User CRUD operations

# This points to a (hypothetical for now) token URL. 
# Even if we don't have a direct /token endpoint for user/pass login,
# OAuth2PasswordBearer needs a tokenUrl. We can point it to one of our auth routes.
# For "Sign in with Google", the token is obtained differently, but this scheme is for header parsing.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login/google") 
                                    # Or any valid endpoint, it's mostly for Swagger UI documentation

async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> UserModel:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = decode_access_token(token)
    if not token_data or not token_data.subject:
        # decode_access_token returning None means token was invalid, expired, or sub missing
        raise credentials_exception
    
    try:
        user_id = int(token_data.subject) # Assuming subject is user_id and it's an integer
    except ValueError:
        # Subject was not a valid integer
        raise credentials_exception
        
    db_user = crud_user.get(db, id=user_id) # Use the generic get from CRUDBase
    if db_user is None:
        raise credentials_exception
    
    # You could add checks here like: if not db_user.is_active: raise HTTPException(...)
    return db_user

# Optional: A dependency for superuser access if you implement roles
# def get_current_active_superuser(current_user: UserModel = Depends(get_current_user)) -> UserModel:
#     if not crud_user.is_superuser(current_user): # Assumes is_superuser method/property in CRUDUser or UserModel
#         raise HTTPException(status_code=403, detail="The user doesn't have enough privileges")
#     return current_user