# app/config.py
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # API settings
    app_name: str = "Developer Career Compass"
    environment: str = "development"
    debug: bool = True
    
    # CORS settings
    cors_origins: List[str] = [
        "http://localhost:3001",
        "https://chiholiu.com",
        "https://www.chiholiu.com",
    ]
    
    @property
    def allow_credentials(self) -> bool:
        """Alleen credentials toestaan in development"""
        return self.environment != "production"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

settings = Settings()