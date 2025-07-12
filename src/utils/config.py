from pydantic_settings import BaseSettings

class AppConfig(BaseSettings):
    debug: bool = False
    log_level: str = "INFO"
    port: int = 8000
    
    # OpenAI Configuration
    openai_api_key: str = ""
    openai_base_url: str = ""  # For proxy or alternative APIs (e.g., Azure OpenAI)
    openai_model: str = "gpt-4"
    openai_max_tokens: int = 150
    openai_temperature: float = 0.3
    openai_timeout: int = 30
    
    # Slack Configuration
    slack_bot_token: str = ""
    slack_signing_secret: str = ""
    slack_app_token: str = ""
    slack_socket_mode: bool = False
    slack_channel_id: str = ""
    # Workflow Configuration
    workflow_config_path: str = "./config/workflows"
    default_workflow: str = "knowledge_base"  # Default to knowledge base lookup for unknown queries

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

config = AppConfig()