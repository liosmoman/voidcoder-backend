import os
# from dotenv import load_dotenv # We'll let Pydantic handle .env loading directly
from pydantic_settings import BaseSettings, SettingsConfigDict # Import SettingsConfigDict
from typing import List, Optional

# env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
# dotenv_loaded = load_dotenv(dotenv_path=env_path) # REMOVE this global load_dotenv

# raw_db_url_from_env = os.getenv("DATABASE_URL")

class Settings(BaseSettings):
    PROJECT_NAME: str = "VoidCoder"
    PROJECT_VERSION: str = "0.1.0"

    DATABASE_URL: str
    GOOGLE_CLOUD_PROJECT: Optional[str] = None # Making this optional, provide default None
    GEMINI_API_KEY: Optional[str] = None

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    GOOGLE_OAUTH_CLIENT_ID: Optional[str] = None  # Or str if always required from .env
    GOOGLE_OAUTH_CLIENT_SECRET: Optional[str] = None # Or str if always required
    GOOGLE_OAUTH_REDIRECT_URI: Optional[str] = None # Or str if it MUST be in .env

    API_V1_STR: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost", "http://localhost:8000"]

    # OpenRouter API Settings
    OPENROUTER_API_KEY: Optional[str] = None # Make it optional if Gemini might still be used
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1" # Default value
    OPENROUTER_MODEL_IDENTIFIER: Optional[str] = "google/gemini-2.5-pro-preview-06-05"
    OPENROUTER_PLANNER_MODEL_IDENTIFIER: Optional[str] = "google/gemini-2.5-pro-preview-06-05" # For planner
    OVERALL_PROJECT_REQUIREMENTS: str = """Create detailed components with these requirements:
1. Use 'use client' directive for client-side components.
2. Style with Tailwind CSS utility classes for responsive design.
3. Use Lucide React for icons (from lucide-react package). Do NOT use other UI libraries unless requested.
4. Use stock photos from picsum.photos where appropriate, only valid URLs you know exist (e.g., https://picsum.photos/seed/unique_seed_1/1200/800).
5. Configure next.config.js image remotePatterns to enable stock photos from picsum.photos for the 'picsum.photos' hostname.
6. If multiple pages are described, create a root layout.tsx page that wraps necessary navigation items to all pages.
7. MUST implement the navigation elements in their rightful place (e.g., Top header, Left sidebar).
8. Accurately implement necessary grid layouts and responsive design.
9. Follow proper import practices (e.g., use @/ path aliases if standard for the project).
10. Update the primary page.tsx (e.g., src/app/page.tsx) with the comprehensive code for the main described page or landing page.
11. You MUST complete the entire code structure for all described pages/components before stopping.
12. Ensure all HTML is semantic and accessible (ARIA attributes where appropriate).
\n"""

    # Active AI Provider Setting
    ACTIVE_AI_PROVIDER: str = "GEMINI" # Default to GEMINI if not set in .env

    # Use a comma-separated string for .env, then parse into a list
    BACKEND_CORS_ORIGINS_CSV: str = "http://localhost:3000,http://127.0.0.1:3000" # Sensible default

    @property
    def parsed_cors_origins(self) -> List[str]: # Renamed property for clarity
        if isinstance(self.BACKEND_CORS_ORIGINS_CSV, str):
            return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS_CSV.split(",") if origin.strip()]
        return [] # Return empty list if not a string (e.g. if directly set as list by other means)

    # Pydantic V2 way to configure .env file loading for BaseSettings
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'),
        env_file_encoding='utf-8',
        extra='ignore'
    )

settings = Settings()

# Debug print to check active provider
# Debug print for CORS origins being used by FastAPI
