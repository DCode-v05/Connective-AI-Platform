import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

    GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")
    NOTION_CLIENT_ID = os.environ.get("NOTION_CLIENT_ID")
    NOTION_CLIENT_SECRET = os.environ.get("NOTION_CLIENT_SECRET")
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
    SLACK_CLIENT_ID = os.environ.get("SLACK_CLIENT_ID")
    SLACK_CLIENT_SECRET = os.environ.get("SLACK_CLIENT_SECRET")
    SALESFORCE_CLIENT_ID = os.environ.get("SALESFORCE_CLIENT_ID")
    SALESFORCE_CLIENT_SECRET = os.environ.get("SALESFORCE_CLIENT_SECRET")
    BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY")

    JWT_SECRET = os.environ.get("JWT_SECRET", "default_secret_key_change_me")
    JWT_EXPIRY_MINUTES = int(os.environ.get("JWT_EXPIRY_MINUTES", "60"))

    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    BACKEND_PORT = int(os.environ.get("PORT", "3000"))

settings = Settings()