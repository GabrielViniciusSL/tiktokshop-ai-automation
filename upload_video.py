import os, requests
from dotenv import load_dotenv
load_dotenv()
ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN")
headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

# 1) upload
with open("video_teste.mp4", "rb") as f:
    files = {"video": ("video_teste.mp4", f, "video/mp4")}
    r = requests.post("https://open.tiktokapis.com/v2/video/upload/", headers=headers, files=files)
    print("UPLOAD:", r.status_code, r.text)
    video_id = r.json().get("data", {}).get("video_id")

# 2) publicar como DRAFT
payload = {"video_id": video_id, "post_mode": "DRAFT"}
r2 = requests.post("https://open.tiktokapis.com/v2/video/publish/", headers=headers, json=payload)
print("PUBLISH:", r2.status_code, r2.text)

