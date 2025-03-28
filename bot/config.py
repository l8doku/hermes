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

    admin_list = os.getenv("ADMINS")
    if not admin_list:
        admin_list = []
    else:
        # list of numberic IDs of admin accounts
        admin_list = [int(x) for x in admin_list.split(",")]

    return {"token": token, "admin_list": admin_list}
