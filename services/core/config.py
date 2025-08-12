from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

def _req(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v

@dataclass(frozen=True)
class Settings:
    tiktok_client_id: str = _req("TIKTOK_CLIENT_ID")
    tiktok_client_secret: str = _req("TIKTOK_CLIENT_SECRET")
    tiktok_redirect_uri: str = _req("TIKTOK_REDIRECT_URI")
    tiktok_scopes: str = os.getenv("TIKTOK_SCOPES", "user.info.basic,video.upload,video.publish")
    supabase_url: str = _req("SUPABASE_URL")
    supabase_key: str = _req("SUPABASE_KEY")
    telegram_bot_token: str = _req("TELEGRAM_BOT_TOKEN")

SETTINGS = Settings()
