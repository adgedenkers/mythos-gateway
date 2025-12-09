# core/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Configuration
    KATUAR_API_KEY: str = ""
    SERAPHET_API_KEY: str = ""
    
    # GitHub Configuration
    GITHUB_TOKEN: str = ""
    GITHUB_USERNAME: str = "adgedenkers"
    GITHUB_REPO: str = "mythos-scroll-library"
    SCROLL_LIBRARY_PATH: str = "/opt/mythos-scroll-library"
        
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str
    NEO4J_PASS: str

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    
    # Other existing settings
    CLOTHING_DATABASE: str = "clothing_store.db"
    UPLOAD_FOLDER: str = "uploads"
    GITHUB_CLOTHING_REPO: str = "mythos-clothing-store"
    DEFAULT_PRICE_MULTIPLIER: float = 1.0
    DEFAULT_GENDER: str = "Unisex"
    DEFAULT_SIZE: str = "XL"

    # Valid API keys (computed property)
    @property
    def valid_api_keys(self) -> set:
        return {self.KATUAR_API_KEY, self.SERAPHET_API_KEY}

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()