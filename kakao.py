#!/usr/bin/env python3
"""Kakao 'send to me' client: token refresh, image upload, feed message."""
import json
import os
import subprocess

import requests

KAUTH = "https://kauth.kakao.com/oauth/token"
KAPI = "https://kapi.kakao.com"
ROOT = os.path.dirname(os.path.abspath(__file__))
ENC_PATH = os.path.join(ROOT, "state", "tokens.enc")
PLAIN_PATH = os.path.join(ROOT, "tokens.json")  # local dev only, gitignored


def _openssl(args, data):
    p = subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt"] + args,
                       input=data, capture_output=True, check=True)
    return p.stdout


def load_tokens():
    if os.environ.get("TOKEN_KEY") and os.path.exists(ENC_PATH):
        with open(ENC_PATH, "rb") as f:
            return json.loads(_openssl(["-d", "-pass", "env:TOKEN_KEY"], f.read()))
    if os.path.exists(PLAIN_PATH):
        with open(PLAIN_PATH, encoding="utf-8") as f:
            return json.load(f)
    raise SystemExit("no tokens found; run get_token.py first")


def save_tokens(tok):
    if os.environ.get("TOKEN_KEY"):
        os.makedirs(os.path.dirname(ENC_PATH), exist_ok=True)
        with open(ENC_PATH, "wb") as f:
            f.write(_openssl(["-e", "-pass", "env:TOKEN_KEY"], json.dumps(tok).encode()))
    if not os.environ.get("CI"):
        with open(PLAIN_PATH, "w", encoding="utf-8") as f:
            json.dump(tok, f, indent=2)


def refresh(tok):
    """Refresh access token; Kakao rotates the refresh token only when it has
    less than one month left, so persist it whenever it appears."""
    data = {"grant_type": "refresh_token",
            "client_id": os.environ["KAKAO_REST_KEY"],
            "refresh_token": tok["refresh_token"]}
    if os.environ.get("KAKAO_CLIENT_SECRET"):
        data["client_secret"] = os.environ["KAKAO_CLIENT_SECRET"]
    r = requests.post(KAUTH, data=data, timeout=30)
    r.raise_for_status()
    j = r.json()
    tok["access_token"] = j["access_token"]
    if "refresh_token" in j:
        tok["refresh_token"] = j["refresh_token"]
    save_tokens(tok)
    return tok


def upload_image(access_token, path):
    """Upload a card PNG to Kakao's image store; returns a public URL."""
    with open(path, "rb") as f:
        r = requests.post(f"{KAPI}/v2/api/talk/message/image/upload",
                          headers={"Authorization": f"Bearer {access_token}"},
                          files={"file": (os.path.basename(path), f, "image/png")},
                          timeout=60)
    r.raise_for_status()
    return r.json()["infos"]["original"]["url"]


def send_feed(access_token, image_url, title, desc, link_url, w=1080, h=1350):
    template = {
        "object_type": "feed",
        "content": {
            "title": title,
            "description": desc,
            "image_url": image_url,
            "image_width": w,
            "image_height": h,
            "link": {"web_url": link_url, "mobile_web_url": link_url},
        },
        "buttons": [{"title": "발음 듣기",
                     "link": {"web_url": link_url, "mobile_web_url": link_url}}],
    }
    r = requests.post(f"{KAPI}/v2/api/talk/memo/default/send",
                      headers={"Authorization": f"Bearer {access_token}"},
                      data={"template_object": json.dumps(template, ensure_ascii=False)},
                      timeout=30)
    r.raise_for_status()
    return r.json()
