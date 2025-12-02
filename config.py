from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str
    
    # Qdrant
    qdrant_url: str
    qdrant_api_key: str
    
    # Gemini AI
    gemini_api_key: str
    
    # Better-Auth
    better_auth_secret: str
    better_auth_url: str = "http://localhost:8000"
    
    # CORS
    frontend_url: str = "http://localhost:3000"
    
    # App Settings
    app_name: str = "Physical AI Textbook"
    debug: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
