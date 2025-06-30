      
# VoidCoder Backend

![VoidCoder Logo](https://raw.githubusercontent.com/your-github-username/your-frontend-repo/main/public/logo192.png) 
*(Note: Replace the logo URL above with a real one once your frontend is on GitHub)*

VoidCoder is a sophisticated, AI-driven application designed to bridge the gap between UI design and code generation. This repository contains the **FastAPI (Python) backend**, which serves as the brain of the operation. It uses a two-stage LLM process to analyze UI images, generate a detailed architectural plan, and create comprehensive, "god-tier" development prompts ready for use in AI coding assistants like Void AI.

## Key Features

*   **Multi-Image Analysis:** Accepts multiple UI screenshots (e.g., for different pages of an app) in a single session.
*   **Two-Stage AI Processing:**
    1.  **Vision Analysis:** Uses a powerful multimodal LLM (via OpenRouter) to perform a deep, structured analysis of each UI image, extracting layout, components, visual style, and semantic meaning.
    2.  **Planner AI:** Feeds the structured analyses into a second, high-level reasoning LLM to generate a coherent, multi-page development plan and component architecture.
*   **User Authentication:** Secure user login and registration handled via Google OAuth 2.0.
*   **Database Persistence:** Saves user analysis sessions, individual image analyses, and final generated prompts to a PostgreSQL database using SQLAlchemy.
*   **Secure API:** Endpoints are protected using JWT (JSON Web Token) authentication.
*   **History & Pagination:** Provides endpoints for users to retrieve their past analysis sessions with efficient pagination.

## Tech Stack

*   **Framework:** [FastAPI](https://fastapi.tiangolo.com/)
*   **Language:** Python 3.11+
*   **Database:** [PostgreSQL](https://www.postgresql.org/)
*   **ORM:** [SQLAlchemy](https://www.sqlalchemy.org/)
*   **Data Validation:** [Pydantic V2](https://docs.pydantic.dev/latest/)
*   **Authentication:** [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2), [python-jose](https://github.com/mpdavis/python-jose) for JWTs
*   **AI Service Integration:** [OpenRouter.ai](https://openrouter.ai/) for access to various vision and planner LLMs.

---

## Setup and Installation

### Prerequisites

*   Python 3.11 or newer
*   PostgreSQL server running
*   An OpenRouter API Key
*   Google OAuth 2.0 Credentials (Client ID & Client Secret)

### 1. Clone the Repository

```bash
    git clone https://github.com/your-github-username/voidcoder_backend.git
    cd voidcoder_backend

2. Create and Activate Virtual Environment

Windows:
      
    python -m venv venv
    .\venv\Scripts\activate

    macOS/Linux:
      
    python3 -m venv venv
    source venv/bin/activate


3. Install Dependencies

Create a requirements.txt file by running pip freeze > requirements.txt in your active virtual environment. Then, to install dependencies:

      
    pip install -r requirements.txt


4. Set Up Environment Variables

    1. Create a .env file in the project root by copying the example file:
          
    # For Windows
    copy .env.example .env

    # For macOS/Linux
    cp .env.example .env


    2. Open the .env file and fill in your actual credentials. This file is git-ignored and must not be committed.

      
# .env.example

# --- Database ---
DATABASE_URL=postgresql://postgres:your_db_password@localhost:5432/voidcoder_db

# --- AI Provider ---
ACTIVE_AI_PROVIDER=OPENROUTER
OPENROUTER_API_KEY=sk-or-your-openrouter-key
OPENROUTER_MODEL_IDENTIFIER=openai/gpt-4.1-nano # Your chosen Vision LLM
OPENROUTER_PLANNER_MODEL_IDENTIFIER=anthropic/claude-3-sonnet-3.5-20240620 # Your chosen Planner LLM

# --- Google OAuth ---
GOOGLE_OAUTH_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-google-client-secret
GOOGLE_OAUTH_REDIRECT_URI=http://127.0.0.1:8000/api/v1/auth/callback/google

# --- JWT Secret ---
# Generate a strong secret key, e.g., using: openssl rand -hex 32
SECRET_KEY=your_strong_random_32_byte_hex_secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30


5. Run the Application

With your virtual environment active, run the following command from the project root:
      
    uvicorn app.main:app --reload


The API will be available at http://127.0.0.1:8000. The interactive documentation can be accessed at http://127.0.0.1:8000/docs.

      
Don't forget to create the `.env.example` file mentioned in the README.
1.  Create a file named `.env.example` in the `voidcoder_backend` root.
2.  Paste the content from the "Set Up Environment Variables" section of the README into it (the part with the empty values).
3.  Save the file.