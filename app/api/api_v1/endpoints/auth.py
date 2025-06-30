# app/api/api_v1/endpoints/auth.py
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from urllib.parse import urlencode # To build query strings

from app.core.config import settings
from app.db.session import get_db
from app.schemas.user import UserCreate, User as UserSchema # Pydantic User schema for response
from app.schemas.token import Token # Pydantic Token schema for response
from app.crud.crud_user import user as crud_user # CRUD operations for User
from app.core.security import create_access_token # JWT creation utility

# For constructing Google OAuth URL (can simplify with google-auth-oauthlib if preferred for more features)
# from google_auth_oauthlib.flow import Flow # Using direct construction for clarity here

router = APIRouter()

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
# Define the scopes your application requests
# Ensure these match what you configured in Google Cloud Console OAuth Consent Screen
SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email", # See user's email address
    "https://www.googleapis.com/auth/userinfo.profile", # See user's basic profile info
    "openid" # Standard OpenID Connect scope
]

@router.get("/login/google", name="auth:google_login")
async def login_google():
    """
    Redirects the user to Google's OAuth 2.0 consent screen.
    """
    if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Google OAuth not configured on server.")

    auth_url_params = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
        "response_type": "code", # We want an authorization code
        "scope": " ".join(SCOPES),
        "access_type": "offline",  # Optional: if you need refresh tokens for long-lived access
        "prompt": "consent",       # Optional: forces consent screen every time, good for dev
        # "state": "some_random_string_for_csrf_protection" # Recommended for CSRF protection
    }
    google_auth_url_base = "https://accounts.google.com/o/oauth2/v2/auth"
    auth_url = f"{google_auth_url_base}?{urlencode(auth_url_params)}"
    
    return RedirectResponse(url=auth_url)

@router.get("/callback/google", name="auth:google_callback") # Removed response_model=Token for pure redirect
async def callback_google(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handles the callback from Google after user authentication.
    Exchanges the authorization code for tokens, fetches user info,
    creates/updates user in DB, and issues a JWT.
    """
    # --- 1. Error Checking from Google Redirect ---
    error = request.query_params.get("error")
    if error:
        error_description = request.query_params.get("error_description", "Unknown Google OAuth error.")
        # In a real app, you'd redirect to a frontend error page
        raise HTTPException(status_code=400, detail=f"Google OAuth Error: {error} - {error_description}")

    # --- 2. Get Authorization Code ---
    code = request.query_params.get("code")
    if not code:
        # In a real app, redirect to frontend error page
        raise HTTPException(status_code=400, detail="Missing authorization code from Google.")

    if not settings.GOOGLE_OAUTH_CLIENT_ID or \
       not settings.GOOGLE_OAUTH_CLIENT_SECRET or \
       not settings.GOOGLE_OAUTH_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Google OAuth not fully configured on server for token exchange.")

    # --- 3. Exchange Authorization Code for Access Token & ID Token ---
    token_payload = {
        "code": code,
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient() as client:
        try:
            token_response = await client.post(GOOGLE_TOKEN_URL, data=token_payload)
            token_response.raise_for_status() # Raise an exception for bad status codes
            token_data = token_response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error exchanging code for token: {e.response.text}")
            raise HTTPException(status_code=400, detail=f"Could not exchange code for token: {e.response.text}")
        except Exception as e:
            print(f"Unexpected error exchanging code for token: {e}")
            raise HTTPException(status_code=500, detail="Error during token exchange.")
            
    google_access_token = token_data.get("access_token")
    # id_token = token_data.get("id_token") # Google ID token - can be decoded to get user info too

    if not google_access_token:
        raise HTTPException(status_code=400, detail="Could not retrieve access token from Google.")

    # --- 4. Fetch User Information from Google using Access Token ---
    userinfo_headers = {"Authorization": f"Bearer {google_access_token}"}
    async with httpx.AsyncClient() as client:
        try:
            userinfo_response = await client.get(GOOGLE_USERINFO_URL, headers=userinfo_headers)
            userinfo_response.raise_for_status()
            user_info = userinfo_response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error fetching user info: {e.response.text}")
            raise HTTPException(status_code=400, detail=f"Could not fetch user info from Google: {e.response.text}")
        except Exception as e:
            print(f"Unexpected error fetching user info: {e}")
            raise HTTPException(status_code=500, detail="Error during user info fetching.")

    user_email = user_info.get("email")
    user_google_id = user_info.get("sub")
    user_display_name = user_info.get("name") 
    user_given_name = user_info.get("given_name") # <--- GET GIVEN_NAME
    # user_family_name = user_info.get("family_name") # Also available
    # user_picture = user_info.get("picture")

    if not user_email or not user_google_id:
        raise HTTPException(status_code=400, detail="Could not retrieve email or user ID from Google profile.")

    db_user = crud_user.get_by_oauth_id(db, oauth_provider="google", oauth_id=user_google_id)
    if not db_user:
        # ... (logic to create user, ensuring display_name is also set)
        # Make sure db_user.display_name is populated with user_display_name (full name) during creation
        user_in_create = UserCreate(
            email=user_email, 
            display_name=user_display_name, # Store full name if available
            oauth_provider="google",
            oauth_id=user_google_id
        )
        db_user = crud_user.create(db, obj_in=user_in_create)
        print(f"Created new user: {db_user.email} with Google ID: {db_user.oauth_id}")
    else:
        # Optionally update user details if they've changed in Google
        if db_user.display_name != user_display_name or \
           (not db_user.oauth_provider or not db_user.oauth_id): # If they previously signed up with email only
            db_user.display_name = user_display_name
            db_user.oauth_provider = "google" # Ensure these are set if they logged in via Google
            db_user.oauth_id = user_google_id
            db.add(db_user) # Add to session before commit
            db.commit()
            db.refresh(db_user)
        print(f"Found existing user: {db_user.email}")
    
    # Pass the necessary info to create_access_token
    app_access_token = create_access_token(
        subject_id=db_user.id,
        user_email=db_user.email, # Pass email
        user_given_name=user_given_name # Pass given_name (first name)
    )

    frontend_callback_url = f"http://localhost:3000/auth/callback?token={app_access_token}"
    return RedirectResponse(url=frontend_callback_url)