import os
from dotenv import load_dotenv, find_dotenv

# Walk up the directory tree to find the nearest .env file.
# Local dev  → finds  UniQuant-main/.env   (the single shared root file)
# Docker     → finds  /app/.env            (backend/.env copied into the container)
load_dotenv(find_dotenv(usecwd=False) or "")


class Settings:
    PROJECT_NAME: str = "UniQuant — Integrated AI Platform"
    API_V1_STR: str = "/api/v1"

    # Path Configuration
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ASSETS_DIR: str = os.path.join(os.path.dirname(BASE_DIR), "assets")
    MODELS_DIR_CREDIT: str = os.path.join(ASSETS_DIR, "models", "credit_risk")

    # API Keys — loaded from .env
    ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")

    # CORS — loaded from .env, fallback to permissive for local dev
    ALLOWED_ORIGINS: list = [
        o.strip()
        for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",")
        if o.strip()
    ]


settings = Settings()
