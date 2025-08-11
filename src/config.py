"""Configuration module to load environment variables."""
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Import os after loading .env to ensure variables are available
import os

# API Keys
MARIADB_URI = os.getenv('MARIADB_URI')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')