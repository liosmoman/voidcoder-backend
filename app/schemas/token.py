# app/schemas/token.py
from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    # This will store the "subject" of the token, e.g., user's email or ID
    subject: Optional[str] = None