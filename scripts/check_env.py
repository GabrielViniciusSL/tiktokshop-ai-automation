from services.core.config import SETTINGS
safe = {
  "tiktok_client_id": SETTINGS.tiktok_client_id[:4] + "***",
  "tiktok_redirect_uri": SETTINGS.tiktok_redirect_uri,
  "supabase_url": SETTINGS.supabase_url,
}
print("ENV OK:", safe)
