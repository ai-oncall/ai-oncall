from pydantic_settings import BaseSettings

class AppConfig(BaseSettings):
    debug: bool = False
    log_level: str = "INFO"
    port: int = 8000
    # Add channel-specific configs as needed

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

config = AppConfig() 