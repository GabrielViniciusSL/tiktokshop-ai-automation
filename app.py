import os, base64, hashlib, secrets
from urllib.parse import urlencode
from flask import Flask, redirect, request, session, jsonify
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "dev-secret")  # coloque algo forte no .env

CLIENT_ID = os.getenv("TIKTOK_CLIENT_ID")
CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET")  # pode não ser necessário no PKCE, mas deixamos
REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI", "http://localhost:5000/callback")
SCOPES = os.getenv("TIKTOK_SCOPES",
    "user.info.basic video.upload video.publish research.video.list research.video.detail research.creator.list")

AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"

def gen_verifier():
    # 43–128 chars, URL-safe
    return base64.urlsafe_b64encode(os.urandom(64)).decode().rstrip("=")

def to_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")

@app.route("/")
def login():
    # 1) gera/ver salva na sessão
    verifier = gen_verifier()
    session["code_verifier"] = verifier
    challenge = to_challenge(verifier)

    params = {
        "client_key": CLIENT_ID,
        "scope": SCOPES,                # espaço entre scopes
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "state": secrets.token_urlsafe(16),
        "code_challenge": challenge,    # 👈 PKCE
        "code_challenge_method": "S256" # 👈 PKCE
    }
    return redirect(f"{AUTH_URL}?{urlencode(params)}")

@app.route("/callback")
def callback():
    if "error" in request.args:
        return jsonify({"error": request.args.get("error"), "desc": request.args.get("error_description")}), 400

    code = request.args.get("code")
    verifier = session.get("code_verifier")
    if not (code and verifier):
        return "Missing code or verifier", 400

    data = {
        "client_key": CLIENT_ID,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "code_verifier": verifier,      # 👈 PKCE
    }
    # alguns apps aceitam/precisam também do client_secret; se der 401, inclua:
    if CLIENT_SECRET:
        data["client_secret"] = CLIENT_SECRET

    resp = requests.post(TOKEN_URL, data=data)
    tok = resp.json()
    # salve com segurança; para demo, só exibimos mascarado
    access = tok.get("access_token", "")
    masked = access[:6] + "..." if access else None
    return jsonify({"token_response": tok, "access_token_masked": masked})

if __name__ == "__main__":
    app.run(port=5000, debug=True)

