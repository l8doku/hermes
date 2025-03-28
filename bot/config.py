import os
from dotenv import load_dotenv
from pathlib import Path


def load_config():
    # Load from .env file if exists
    env_path = Path(".") / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    # Required configuration
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_TOKEN must be set in environment variables")

    return {"token": token}
