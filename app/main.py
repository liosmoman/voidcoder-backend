from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # Ensure this is imported

from app.core.config import settings
from app.db.session import engine 
from app.models import prompt_session # Ensure this is imported if Base is used from it

# Import your API routers
from app.api.api_v1.endpoints import prompts as prompts_router
from app.api.api_v1.endpoints import auth as auth_router
# If you had an auth_router, you would import it like this:
# from app.api.api_v1.endpoints import auth as auth_router

# --- Database Table Creation (MVP Approach) ---
# This attempts to create tables if they don't exist when the app starts.
# For production, Alembic (database migrations) is the recommended way.
try:
    # The Base object needs to know about all your models.
    # If User, PromptSession, GeneratedPrompt are all in prompt_session.py
    # and Base is defined in db.session and imported into prompt_session.py,
    # then this line is correct.
    prompt_session.Base.metadata.create_all(bind=engine)
    print("Database tables checked/created successfully upon startup.")
except Exception as e:
    print(f"Error creating database tables upon startup: {e}")
    # Depending on your policy, you might want the app to exit if DB is not ready
    # or handle this more gracefully.


# --- FastAPI Application Instance ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" # Use the prefix from settings
)


# --- CORS (Cross-Origin Resource Sharing) Middleware ---
# This must be added before any routers that need CORS.
# It allows your React frontend (on localhost:3000) to talk to this backend (on localhost:8000).
if settings.parsed_cors_origins: # Use the property here
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.parsed_cors_origins, # Use the property here
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    print("Warning: No CORS origins configured. Frontend might not connect if on a different origin.")


# --- Root Endpoint ---
@app.get("/", tags=["Root"])
async def read_root():
    """
    A simple root endpoint to check if the API is running.
    """
    return {"message": f"Welcome to {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}"}


# --- Include Your API Routers ---
# All routes defined in prompts_router will now be available under /api/v1/prompts
app.include_router(
    prompts_router.router, # The 'router' object from your prompts.py file
    prefix=settings.API_V1_STR + "/prompts", # Prepends /api/v1/prompts to all routes in this router
    tags=["Prompts"] # Groups these endpoints under "Prompts" in Swagger UI
)
app.include_router(auth_router.router, prefix=settings.API_V1_STR + "/auth", tags=["Authentication"])

# If you create an authentication router later, you would include it like this:
# app.include_router(
#     auth_router.router, 
#     prefix=settings.API_V1_STR + "/auth", 
#     tags=["Authentication"]
# )


# --- Main Execution Block (for running with `python app/main.py`) ---
# This part is mostly for direct execution during development.
# When deploying with Uvicorn directly (e.g., uvicorn app.main:app), this block isn't the primary entry point for Uvicorn.
if __name__ == "__main__":
    import uvicorn
    print("Attempting to start VoidCoder API development server directly using 'python app/main.py'...")
    print("For development with auto-reload, prefer running from project root: 'uvicorn app.main:app --reload'")
    uvicorn.run(
        "app.main:app", # Points to the 'app' instance in this 'app.main' module
        host="0.0.0.0", # Listen on all available network interfaces
        port=8000,      # Listen on port 8000
        reload=True     # Enable auto-reload (though less effective when run this way vs. direct uvicorn command)
    )