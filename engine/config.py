"""Engine settings, loaded from environment / .env."""
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    hermes_dashboard_url: str = os.getenv("HERMES_DASHBOARD_URL", "http://192.168.1.5:30433")
    hermes_api_url: str = os.getenv("HERMES_API_URL", "http://192.168.1.5:30432")
    hermes_api_key: str = os.getenv("HERMES_API_KEY", "")
    hermes_username: str = os.getenv("HERMES_USERNAME", "")
    hermes_password: str = os.getenv("HERMES_PASSWORD", "")
    ollama_pool_url: str = os.getenv("OLLAMA_POOL_URL", "http://192.168.1.5:4000")
    database_url: str = os.getenv("DATABASE_URL", "postgresql://farmhouse:farmhouse@localhost:5433/farmhouse")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6380/0")


settings = Settings()
