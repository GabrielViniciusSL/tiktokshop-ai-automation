import os, requests
from dotenv import load_dotenv
load_dotenv()
ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN")
headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
# endpoint e params podem variar; mostre um request real de pesquisa
url = "https://open.tiktokapis.com/v2/research/video/list/"
params = {"max_count": 5, "query": "beauty"}
r = requests.get(url, headers=headers, params=params)
print(r.status_code, r.json())

